#!/usr/bin/env python3
"""
ETL: monta a tabela horária do modelo a partir dos arquivos BRUTOS — como o
backend faria com o que chega do smart meter GoodWe e dos carregadores OCPP.

    python3 preparar_dataset.py

Entrada (dados/): medidor_galeria_5min.csv.gz, ocpp_meter_values.csv.gz,
ocpp_transacoes.csv, ocpp_status_notification.csv, clima_horario.csv
Saída:  dados/dataset_horario.csv     1 linha por hora (alvos podem ser vazios)
        dados/qualidade_dados.json    o que foi limpo, descartado e preenchido

Tratamentos (cada um corresponde a um defeito comum de telemetria):
  - leituras duplicadas (retransmissão)              → mantém a primeira
  - leituras espúrias (tensão zerada, potência ×10)  → descarta a amostra
  - lacunas do datalogger                            → hora com < 10 de 12 amostras fica sem alvo
  - MeterValues perdidos                             → energia interpolada pelo registrador
  - StopTransaction que nunca chegou                 → fecha a sessão no último MeterValue
  - contador do medidor zerado (troca de medidor)    → não usado: energia sai das potências
  - horas sem clima                                  → interpolação linear até 3 h

O consumo da galeria não é medido diretamente: sai do balanço no ponto de
conexão — galeria = importação − exportação + solar + bateria − vagas.
Se houver gabarito (_gabarito/horario_verdade.csv, só na base simulada), o ETL
compara o que reconstruiu com a verdade.
"""

import json
import os

import numpy as np
import pandas as pd

from calendario import info_dia

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "dados")
COBERTURA_MIN = 10          # amostras de 5 min por hora (de 12)


def ts_local(s):
    return pd.to_datetime(s.astype(str).str[:19])


def main():
    q = {}

    # ------------------------------------------------------------ medidor
    med = pd.read_csv(os.path.join(DADOS, "medidor_galeria_5min.csv.gz"))
    q["medidor_linhas_lidas"] = len(med)
    med["t"] = ts_local(med["timestamp"])
    dup = med.duplicated("t", keep="first")
    q["medidor_duplicadas_removidas"] = int(dup.sum())
    med = med[~dup]
    med = med.sort_values("t")
    # salto isolado: difere > 15 kW da mediana das 2 leituras antes e 2 depois
    viz = med["pmeter_w"].rolling(5, center=True, min_periods=3).median()
    salto = (med["pmeter_w"] - viz).abs() > 15_000
    esp = (med[["v_l1", "v_l2", "v_l3"]].min(axis=1) < 90) | (med["pmeter_w"].abs() > 150_000) | salto
    q["medidor_espurias_removidas"] = int(esp.sum())
    med = med[~esp].set_index("t").sort_index()
    grade = pd.date_range(med.index.min(), med.index.max(), freq="5min")
    q["medidor_amostras_faltando"] = int(len(grade) - len(med))

    # ------------------------------------------------- OCPP: energia por sessão
    mv = pd.read_csv(os.path.join(DADOS, "ocpp_meter_values.csv.gz"))
    q["meter_values_lidos"] = len(mv)
    mv["t"] = ts_local(mv["timestamp"])
    d = mv.duplicated(["transaction_id", "t"], keep="first")
    q["meter_values_duplicados_removidos"] = int(d.sum())
    mv = mv[~d]
    tx = pd.read_csv(os.path.join(DADOS, "ocpp_transacoes.csv"))
    tx["t0"] = ts_local(tx["timestamp_start"])
    sem_stop = tx["timestamp_stop"].isna()
    q["transacoes_sem_stop_fechadas_pelo_ultimo_meter_value"] = int(sem_stop.sum())

    # registrador de energia de cada sessão numa grade de 5 min; amostras
    # perdidas são interpoladas no tempo (o registrador é cumulativo)
    partes = []
    mv = mv.sort_values(["transaction_id", "t"])
    grupos = dict(tuple(mv.groupby("transaction_id")))
    preenchidos = 0
    for r in tx.itertuples():
        g = grupos.get(r.transaction_id)
        if g is None:
            continue
        fim = g["t"].max() if pd.isna(r.timestamp_stop) else ts_local(pd.Series([r.timestamp_stop])).iloc[0]
        idx = pd.date_range(r.t0, fim, freq="5min")
        reg = pd.Series(np.nan, index=idx)
        reg.iloc[0] = r.meter_start_wh
        reg.loc[g["t"][g["t"].isin(idx)].values] = g.loc[g["t"].isin(idx), "energy_active_import_register_wh"].values
        preenchidos += int(reg.isna().sum())
        reg = reg.interpolate(method="time").ffill()
        e = reg.diff().iloc[1:].clip(lower=0) / 1000            # kWh no intervalo que TERMINA em t
        partes.append(pd.DataFrame({"t": e.index, "kwh": e.values}))
    q["meter_values_interpolados"] = preenchidos
    ev5 = pd.concat(partes).groupby("t")["kwh"].sum()
    ev5 = ev5.reindex(grade, fill_value=0.0)                    # sem sessão = 0 kWh

    # ---------------------------------------------- galeria por balanço de potência
    m = med.reindex(grade)
    rede_kw = -m["pmeter_w"] / 1000                              # > 0 importação
    ev_kw = ev5 * 12
    galeria_kw = rede_kw + m["ppv_w"] / 1000 + m["pbattery_w"] / 1000 - ev_kw
    ok = m["pmeter_w"].notna()
    inicio_hora = (grade - pd.Timedelta(minutes=5)).floor("h")  # amostra em t cobre (t-5, t]
    df5 = pd.DataFrame({"h": inicio_hora, "gal": galeria_kw.values, "pv": (m["ppv_w"] / 1000).values,
                        "rede": rede_kw.values, "ev": ev5.values, "ok": ok.values})
    g = df5.groupby("h")
    hr = pd.DataFrame({
        "amostras_medidor": g["ok"].sum(),
        "galeria_kwh": g["gal"].mean() * 1.0,
        "solar_kwh": g["pv"].mean() * 1.0,
        "ev_kwh": g["ev"].sum(),
    })
    sem_cob = hr["amostras_medidor"] < COBERTURA_MIN
    hr.loc[sem_cob, ["galeria_kwh", "solar_kwh"]] = np.nan
    q["horas_sem_cobertura_do_medidor"] = int(sem_cob.sum())
    q15 = pd.Series(rede_kw.values, index=grade - pd.Timedelta(minutes=5)).resample("15min").mean()
    hr["demanda_rede_pico_kw"] = q15.resample("h").max().reindex(hr.index)
    hr.loc[sem_cob, "demanda_rede_pico_kw"] = np.nan
    e15 = pd.Series(ev_kw.values, index=grade - pd.Timedelta(minutes=5)).resample("15min").mean()
    hr["ev_pico_kw"] = e15.resample("h").max().reindex(hr.index)

    # --------------------------------------------- vagas operando (StatusNotification)
    st = pd.read_csv(os.path.join(DADOS, "ocpp_status_notification.csv"), keep_default_na=False)
    st["t"] = ts_local(st["timestamp"])
    horas = hr.index
    grade5 = pd.date_range(horas[0], horas[-1] + pd.Timedelta(minutes=55), freq="5min")
    em_falha = np.zeros((st["charge_point_id"].nunique(), len(horas)), bool)
    for k, (cp, s) in enumerate(st.sort_values("t", kind="stable").groupby("charge_point_id")):
        estado = s.set_index("t")["status"].eq("Faulted")
        estado = estado[~estado.index.duplicated(keep="last")]
        linha = estado.reindex(estado.index.union(grade5)).ffill().fillna(False).reindex(grade5).astype(bool)
        # falha em qualquer instante da hora conta como vaga fora
        em_falha[k] = linha.groupby(grade5.floor("h")).max().reindex(horas, fill_value=False).values
    hr["vagas_operando"] = len(em_falha) - em_falha.sum(axis=0)
    hr["sessoes_iniciadas"] = tx.groupby(tx["t0"].dt.floor("h")).size().reindex(horas, fill_value=0)

    # --------------------------------------------------------------- clima
    cl = pd.read_csv(os.path.join(DADOS, "clima_horario.csv"))
    cl["t"] = ts_local(cl["time"])
    cl = cl.set_index("t").drop(columns=["time"]).reindex(horas)
    q["clima_horas_preenchidas"] = int(cl.isna().any(axis=1).sum())
    cl = cl.interpolate(limit=3, limit_direction="both")
    hr = hr.join(cl)

    # ----------------------------------------------------------- calendário
    cal = pd.DataFrame([info_dia(dd) for dd in pd.unique(horas.date)]).set_index("data")
    hr["_data"] = horas.date
    hr = hr.join(cal, on="_data").drop(columns="_data")

    hr.index.name = "timestamp"
    hr = hr.reset_index()
    hr["timestamp"] = hr["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00"
    num = ["galeria_kwh", "solar_kwh", "ev_kwh", "demanda_rede_pico_kw", "ev_pico_kw"]
    hr[num] = hr[num].round(3)
    hr = hr.drop(columns=["amostras_medidor"])
    hr.to_csv(os.path.join(DADOS, "dataset_horario.csv"), index=False)
    q["horas_total"] = len(hr)
    q["horas_com_alvo_galeria"] = int(hr["galeria_kwh"].notna().sum())

    # ------------------------------------------------- confere com o gabarito
    gab_p = os.path.join(DADOS, "_gabarito", "horario_verdade.csv")
    if os.path.exists(gab_p):
        gab = pd.read_csv(gab_p).set_index("timestamp")
        x = hr.set_index("timestamp").join(gab, rsuffix="_verdade", how="inner")
        conf = {}
        for c in ["galeria_kwh", "ev_kwh", "solar_kwh"]:
            v = x[[c, c + "_verdade"]].dropna()
            conf[c] = {"erro_medio_abs_kwh": round(float((v[c] - v[c + "_verdade"]).abs().mean()), 4),
                       "erro_total_pct": round(float((v[c].sum() / v[c + "_verdade"].sum() - 1) * 100), 3)}
        v = x[["vagas_operando", "vagas_operando_verdade"]].dropna()
        conf["vagas_operando_horas_iguais_pct"] = round(float((v.iloc[:, 0] == v.iloc[:, 1]).mean() * 100), 2)
        q["conferencia_com_gabarito"] = conf

    with open(os.path.join(DADOS, "qualidade_dados.json"), "w") as f:
        json.dump(q, f, ensure_ascii=False, indent=1)
    print(json.dumps(q, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
