"""
Leva para o app o que o notebook ChargeGrid_ML.ipynb decidiu.

    from exportar_app import exportar
    exportar(modelos, avaliacao, perfis)

Gera app/src/ml/previsao-dados.js (constante ML_DADOS, embutida pelo build) e
resultados/paridade_js.json (usado por testar_paridade_js.py).
"""

import json
import os

import numpy as np
import pandas as pd

from variaveis import montar, nivel_ev

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "dados")
APP_ML = os.path.join(BASE, "..", "app", "src", "ml")
RES = os.path.join(BASE, "resultados")

GRUPOS = {
    "Horário de funcionamento": ["hora", "galeria_aberta", "eletroposto_aberto"],
    "Histórico recente": ["media_4sem_galeria_kwh", "media_4sem_ev_kwh"],
    "Dia da semana": ["dia_semana"],
    "Temperatura": ["temperatura_c", "umidade_pct"],
    "Sol (irradiância)": ["irradiancia_w_m2", "nuvens_pct"],
    "Chuva": ["chuva_mm"],
    "Feriados e datas comerciais": ["feriado", "fator_comercial"],
    "Vagas operando": ["vagas_operando"],
}


def _arvores(rf):
    """Random Forest → listas compactas por árvore (o app tira a média das folhas)."""
    out = []
    for est in rf.estimators_:
        tr = est.tree_
        folha = tr.children_left == -1
        mg = getattr(tr, "missing_go_to_left", np.zeros(tr.node_count, dtype=np.uint8))
        out.append({
            "f": np.where(folha, -1, tr.feature).astype(int).tolist(),
            "t": [0 if folha[i] else float(tr.threshold[i]) for i in range(tr.node_count)],
            "l": tr.children_left.astype(int).tolist(),
            "r": tr.children_right.astype(int).tolist(),
            "v": [round(float(tr.value[i, 0, 0]), 6) if folha[i] else 0 for i in range(tr.node_count)],
            "m": [int(x) for x in mg],
        })
    return out


def _importancia(rf, colunas):
    imp = dict(zip(colunas, rf.feature_importances_))
    g = {nome: round(sum(imp.get(c, 0) for c in cols) * 100, 1) for nome, cols in GRUPOS.items()}
    return {k: v for k, v in sorted(g.items(), key=lambda kv: -kv[1]) if v > 0}


def semana():
    """Histórico das últimas 4 semanas + insumos dos 7 dias previstos (12 a 18/10/2026),
    já na tabela da aula (variaveis.montar). Devolve também os brutos usados."""
    df = pd.read_csv(os.path.join(DADOS, "dataset_horario.csv"))
    df["t"] = pd.to_datetime(df["timestamp"].str[:19])
    hist = df.iloc[-24 * 42:].copy()            # 6 semanas: média de 4 semanas (672 h) + janela do nível (168 h)
    prev = pd.read_csv(os.path.join(DADOS, "previsao_clima_open_meteo.csv"))
    cal = pd.read_csv(os.path.join(DADOS, "calendario_previsao.csv"))
    prev["data"] = prev["time"].str[:10]
    fut = prev.merge(cal, on="data", how="left")
    fut["timestamp"] = fut["time"]
    fut["vagas_operando"] = 3                    # Vaga 03 em falha na última leitura
    for c in ["ev_kwh", "galeria_kwh", "demanda_rede_pico_kw", "solar_kwh"]:
        fut[c] = np.nan
    cols = ["timestamp", "ev_kwh", "galeria_kwh", "demanda_rede_pico_kw", "solar_kwh", "vagas_operando",
            "dia_semana", "feriado", "fator_comercial", "abre", "fecha", "ep_abre", "ep_fecha",
            "temperature_2m", "shortwave_radiation", "cloud_cover", "precipitation", "relative_humidity_2m"]
    junto = montar(pd.concat([hist[cols], fut[cols]], ignore_index=True))
    junto["nivel_ev"] = nivel_ev(junto)          # janela de 168 h atravessa histórico → semana prevista
    futX = junto.iloc[len(hist):].reset_index(drop=True)
    return df, hist, prev, cal, fut, futX


def exportar(modelos, avaliacao, perfis, nivel_previsto=None):
    """
    modelos:   {"galeria": (rf, colunas_X, escala), "ev": (...)} já treinados com todo o histórico;
               escala None (prevê kWh) ou "nivel_ev" (prevê kWh ÷ nível recente)
    avaliacao: {"galeria"|"ev": {"metricas": {...}, "residuos": DataFrame(data_hora, real, previsto, baseline)}}
    perfis:    dict do K-Means (média/desvio das variáveis, centróides, nomes, ações)
    """
    df, hist, prev, cal, fut, futX = semana()

    # geração solar prevista: física simples calibrada no histórico
    v = df[["shortwave_radiation", "temperature_2m", "solar_kwh"]].dropna()
    g = v["shortwave_radiation"]; x = g * (1 - 0.004 * (v["temperature_2m"] + 0.03 * g - 25))
    k_solar = round(float((x * v["solar_kwh"]).sum() / (x * x).sum()), 6)

    out_modelos, paridade, intervalos, metricas, backtest = {}, {}, {}, {}, {}
    for alvo, (rf, colunas, escala) in modelos.items():
        out_modelos[alvo] = {"tipo": "random_forest", "features": colunas, "arvores": _arvores(rf), "escala": escala,
                             "n_treino": int(avaliacao[alvo]["n_treino_final"]), "n_arvores": len(rf.estimators_),
                             "profundidade_max": rf.max_depth}
        tab = montar(df).dropna(subset=colunas)
        amostra = tab[colunas].sample(400, random_state=1)
        Xf = futX[colunas]
        assert Xf.notna().all().all(), "faltou insumo para a semana prevista"
        fator = futX["nivel_ev"].values if escala == "nivel_ev" else 1.0
        paridade[alvo] = {"X": amostra.values.tolist(), "y": rf.predict(amostra).tolist(),   # saída crua das árvores
                          "futuro": (rf.predict(Xf) * fator).round(4).tolist()}
        r = avaliacao[alvo]["residuos"].copy()
        r["hora"] = r["data_hora"].dt.hour
        r["d"] = r["data_hora"].dt.normalize()
        dia = r.groupby("d")[["real", "previsto"]].sum()
        dia = dia[r.groupby("d").size() == 24]
        sem = r.assign(w=r["data_hora"].dt.to_period("W")).groupby("w")[["real", "previsto"]].sum().iloc[1:-1]
        intervalos[alvo] = {
            "hora_q80_kwh": [round(float((r.loc[r["hora"] == h, "real"] - r.loc[r["hora"] == h, "previsto"]).abs().quantile(0.8)), 3) for h in range(24)],
            "dia_q80_rel": round(float(((dia["real"] - dia["previsto"]) / dia["previsto"]).abs().quantile(0.8)), 4),
            "semana_q80_rel": round(float(((sem["real"] - sem["previsto"]) / sem["previsto"]).abs().quantile(0.8)), 4),
        }
        m = dict(avaliacao[alvo]["metricas"])
        m["importancia_grupos"] = _importancia(rf, colunas)
        metricas[alvo] = m
        ult = dia.iloc[-14:]
        backtest[alvo] = {"datas": [d.strftime("%Y-%m-%d") for d in ult.index],
                          "real": [round(float(x), 1) for x in ult["real"]],
                          "previsto": [round(float(x), 1) for x in ult["previsto"]]}

    mes10 = df[df["t"].dt.month == 10]
    abertas = ((hist["t"].dt.hour >= hist["ep_abre"]) & (hist["t"].dt.hour < hist["ep_fecha"])).iloc[-672:].sum()
    dados = {
        "versao": "2026-10-11",
        "geradoEm": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M"),
        "ultimaLeitura": "2026-10-11T23:55:00-03:00",
        "galeria": "Galeria Pátio Norte",
        "contratadaKw": 55.0, "margemDlm": 0.12, "bessKwh": 30.0, "bessKw": 15.0, "kwVaga": 7.0,
        "kSolar": k_solar,
        "sessoesDia": round(float(hist["sessoes_iniciadas"].iloc[-672:].sum() / 28), 1),
        "utilizacaoVagas": round(float(hist["ev_kwh"].iloc[-672:].sum() / (4 * 7.0 * abertas)), 3),
        "historico": {
            "inicio": hist["timestamp"].iloc[0],
            "ev": [None if pd.isna(x) else round(float(x), 3) for x in hist["ev_kwh"]],
            "galeria": [None if pd.isna(x) else round(float(x), 3) for x in hist["galeria_kwh"]],
        },
        "futuro": {
            "inicio": fut["timestamp"].iloc[0],
            "temperatura": fut["temperature_2m"].tolist(), "irradiancia": fut["shortwave_radiation"].tolist(),
            "nebulosidade": fut["cloud_cover"].tolist(), "precipitacao": fut["precipitation"].tolist(),
            "umidade": fut["relative_humidity_2m"].tolist(), "emitidaEm": prev["emitida_em"].iloc[0],
        },
        "calendario": cal.fillna("").to_dict(orient="records"),
        "normais": {
            "temperatura": [round(float(x), 1) for x in mes10.groupby(mes10["t"].dt.hour)["temperature_2m"].mean()],
            "irradiancia": [round(float(x), 0) for x in mes10.groupby(mes10["t"].dt.hour)["shortwave_radiation"].mean()],
            "nebulosidade": [round(float(x), 0) for x in mes10.groupby(mes10["t"].dt.hour)["cloud_cover"].mean()],
            "umidade": [round(float(x), 0) for x in mes10.groupby(mes10["t"].dt.hour)["relative_humidity_2m"].mean()],
        },
        "intervalos": intervalos,
        "metricas": metricas,
        "backtest": backtest,
        "perfis": perfis,
        # Parte 1 do notebook: classe prevista (Baixa/Média/Alta) para cada hora da semana
        "nivelPrevisto": nivel_previsto,
        "vagasNaPrevisao": 3,
        "modelos": out_modelos,
    }
    os.makedirs(APP_ML, exist_ok=True); os.makedirs(RES, exist_ok=True)
    js = ("// GERADO pelo notebook inteligencia/ChargeGrid_ML.ipynb (exportar_app.py) — não edite à mão.\n"
          "// Random Forest de regressão (lógica da aula de SERS) + insumos da semana + perfis de dia (K-Means).\n"
          "// Em produção estes dados viriam do Supabase (tabelas previsoes/leituras_energia).\n"
          "const ML_DADOS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n")
    with open(os.path.join(APP_ML, "previsao-dados.js"), "w", encoding="utf-8") as f:
        f.write(js)
    with open(os.path.join(RES, "paridade_js.json"), "w") as f:
        json.dump(paridade, f)
    return {"kb": round(len(js.encode()) / 1024), "k_solar": k_solar,
            "previsao_d1": {a: round(sum(paridade[a]["futuro"][:24]), 1) for a in paridade}}
