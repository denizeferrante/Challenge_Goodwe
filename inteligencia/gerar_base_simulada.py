#!/usr/bin/env python3
"""
Gera a base simulada da Galeria Pátio Norte — como se fosse o histórico real
coletado pelo smart meter GoodWe (via inversor/SEMS) e pelos 4 carregadores
HCA G2 falando OCPP 1.6 com o backend.

    python3 gerar_base_simulada.py                         # clima simulado
    python3 gerar_base_simulada.py --clima-real clima.csv  # clima real (baixar_clima_real.py)

Saídas em dados/ (ver README.md para o dicionário de dados):

  Brutos, como chegam dos equipamentos
    medidor_galeria_5min.csv.gz     smart meter GoodWe + inversor + BESS, 5 min
    ocpp_meter_values.csv.gz        MeterValues (Sample.Periodic, 5 min) por conector
    ocpp_transacoes.csv             StartTransaction / StopTransaction
    ocpp_status_notification.csv    StatusNotification (inclui falhas)
    clima_horario.csv               histórico no formato da API Open-Meteo
    previsao_clima_open_meteo.csv   previsão emitida em 11/10 23h para os 7 dias seguintes

  No formato das tabelas do Supabase (diagrama-er-supabase.mermaid)
    supabase/leituras_energia.csv, supabase/recargas.csv,
    supabase/recarga_eventos.csv, supabase/alocacoes_potencia.csv,
    supabase/veiculos.csv

  Gabarito (só existe porque a base é simulada)
    _gabarito/horario_verdade.csv   kWh reais por hora, para conferir o ETL

  A tabela do modelo (dataset_horario.csv) NÃO sai daqui: quem a monta é o
  preparar_dataset.py, lendo os arquivos brutos acima — com as lacunas,
  duplicatas e falhas que equipamento real produz.

Toda a física e o comportamento estão parametrizados em CFG. Semente fixa:
rodar de novo gera exatamente a mesma base.
"""

import argparse
import gzip
import math
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from calendario import info_dia

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "dados")

CFG = {
    "inicio": date(2025, 1, 1),
    "fim": date(2026, 10, 11),           # última leitura: 11/10/2026 23:55
    "dias_previsao": 7,                  # janela que o app vai prever
    "semente": 20261012,
    "lat": -23.561414, "lon": -46.655881,  # Av. Paulista, 1578
    "galeria_id": 1,
    "galeria": "Galeria Pátio Norte",
    "metragem_m2": 2400,
    "demanda_contratada_kw": 55.0,
    "margem_dlm": 0.12,                  # 12% de margem, como no app
    # geração — mesmos kWp do Painel do app
    "pv": {"cobertura": (43.2, 1.00), "fachada": (9.6, 0.55), "carport": (14.4, 0.90)},
    "perdas_sistema": 0.79,               # cabos, inversor, mismatch (sem sujeira)
    "coef_temp_pv": -0.004,              # %/°C acima de 25 °C de célula
    # BESS
    "bess_kwh": 30.0, "bess_kw": 15.0, "bess_soc_min": 0.10,
    "ponta": (17, 21),                   # descarga do BESS na faixa de ponta
    # eletroposto
    "carregadores": [
        ("GWH7-2841-BR", "PN-EVSE-01", "Vaga 01"),
        ("GWH7-2847-BR", "PN-EVSE-02", "Vaga 02"),
        ("GWH7-2853-BR", "PN-EVSE-03", "Vaga 03"),
        ("GWH7-2860-BR", "PN-EVSE-04", "Vaga 04"),
    ],
    "kw_carregador": 7.0,
    "tensao_ev": 220.0,
    "preco_base": [(date(2025, 1, 1), 1.99), (date(2025, 9, 1), 2.09), (date(2026, 3, 1), 2.19)],
    "motoristas": 900,
    # chegadas por hora no pico do perfil (jan/2025) e crescimento anual da
    # procura. Calibrado para ~12% de utilização no início e ~20% no fim:
    # carregador público AC costuma ter utilização baixa (estudos no Reino
    # Unido acham mediana abaixo de 5%); uma galeria bem localizada fica acima.
    "lambda_ev": 0.34,
    "crescimento_ev": 1.45,
    # medidor do condomínio: áreas comuns, climatização central, iluminação e
    # estacionamento. As lojas têm medidor próprio da Enel e não entram aqui.
    "retrofit_led": date(2026, 3, 16),    # troca para LED: iluminação 8,5 → 6,0 kW
}

# frota elétrica comum no Brasil: (modelo, bateria útil kWh, AC máx kW, peso)
# valores aproximados de ficha técnica, suficientes para a simulação
FROTA = [
    ("BYD Dolphin Mini", 38.0, 6.6, 0.27),
    ("BYD Dolphin", 44.9, 6.6, 0.17),
    ("BYD Song Plus DM-i (PHEV)", 18.3, 6.6, 0.10),
    ("GWM Ora 03", 48.0, 6.6, 0.08),
    ("BYD Yuan Pro", 45.1, 6.6, 0.06),
    ("Volvo EX30", 51.0, 7.0, 0.07),
    ("Renault Kwid E-Tech", 26.8, 6.6, 0.06),
    ("BYD Seal", 82.5, 7.0, 0.05),
    ("Chevrolet Bolt EUV", 65.0, 7.0, 0.04),
    ("Peugeot e-2008", 50.0, 7.0, 0.04),
    ("BMW iX1", 64.7, 7.0, 0.03),
    ("GWM Haval H6 PHEV", 34.0, 6.6, 0.03),
]

rng = np.random.default_rng(CFG["semente"])


# --------------------------------------------------------------------- clima
def posicao_solar(ts: pd.DatetimeIndex):
    """cos(zênite) para timestamps locais (UTC-3, sem horário de verão)."""
    doy = ts.dayofyear.values
    hora = ts.hour.values + ts.minute.values / 60.0
    g = 2 * math.pi / 365 * (doy - 1 + (hora - 12) / 24)
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    utc = hora + 3.0
    hora_solar = utc * 60 + eqt + 4 * CFG["lon"]
    ang = np.radians(hora_solar / 4 - 180)
    lat = math.radians(CFG["lat"])
    cosz = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(ang)
    return np.clip(cosz, 0, 1)


def ghi_ceu_claro(cosz):
    """Modelo de Haurwitz (W/m²)."""
    out = np.zeros_like(cosz)
    m = cosz > 0.01
    out[m] = 1098 * cosz[m] * np.exp(-0.059 / cosz[m])
    return out


# ajusta o volume de chuva de cada mês à normal aproximada de São Paulo
# (verão ~250–300 mm, inverno ~35–55 mm, outubro ~125 mm)
FATOR_CHUVA_MES = {1: 0.85, 2: 0.88, 3: 0.75, 4: 0.6, 5: 1.05, 6: 1.25, 7: 1.8, 8: 2.7,
                   9: 1.7, 10: 1.7, 11: 0.5, 12: 0.79}


def carregar_clima_real(caminho, dias):
    """Lê um CSV horário no formato da Open-Meteo (ver baixar_clima_real.py)
    e devolve as mesmas colunas de gerar_clima()."""
    c = pd.read_csv(caminho)
    c["time"] = pd.to_datetime(c["time"].astype(str).str[:16])
    c = c.set_index("time").sort_index()
    grade = pd.date_range(datetime(dias[0].year, dias[0].month, dias[0].day),
                          datetime(dias[-1].year, dias[-1].month, dias[-1].day, 23), freq="h")
    c = c.reindex(grade).interpolate(limit=3).ffill().bfill()
    falta = [k for k in ["temperature_2m", "cloud_cover", "precipitation", "relative_humidity_2m", "shortwave_radiation"] if k not in c]
    if falta:
        raise SystemExit("clima real sem as colunas " + ", ".join(falta))
    c = c.reset_index().rename(columns={"index": "time"})
    return c[["time", "temperature_2m", "cloud_cover", "precipitation", "relative_humidity_2m", "shortwave_radiation"]]


def gerar_clima(dias):
    """Clima horário de São Paulo: sazonalidade, frentes frias, tardes de
    verão chuvosas. Colunas com os nomes da API Open-Meteo."""
    n = len(dias)
    doy = np.array([d.timetuple().tm_yday for d in dias])
    s = np.cos(2 * np.pi * (doy - 20) / 365)          # +1 verão, -1 inverno
    p_chuva = 0.36 + 0.21 * s
    umido = np.zeros(n, bool)
    anom = np.zeros(n)
    for i in range(n):
        p = p_chuva[i] + (0.22 if i and umido[i - 1] else -0.06)
        umido[i] = rng.random() < np.clip(p, 0.03, 0.9)
        anom[i] = (0.72 * anom[i - 1] if i else 0) + rng.normal(0, 1.55)
    nuvem_dia = np.where(umido, rng.beta(5, 2, n), rng.beta(1.3, 3.4, n))
    # calibrado nas normais aproximadas do INMET para São Paulo (1991–2020):
    # máx ~28 °C / mín ~19 °C em janeiro; máx ~22 °C / mín ~12 °C em julho
    t_media = 20.9 + 3.0 * s + anom - 1.6 * (nuvem_dia - 0.4)
    amplitude = 4.6 + 6.2 * (1 - nuvem_dia)

    linhas = []
    for i, d in enumerate(dias):
        ar = 0.0
        for h in range(24):
            ar = 0.7 * ar + rng.normal(0, 0.09)
            conv = 0.18 * max(s[i], 0) * math.exp(-((h - 16.5) ** 2) / 6)  # convecção de verão
            nuvem = float(np.clip(nuvem_dia[i] + ar + conv, 0, 1))
            temp = t_media[i] + amplitude[i] / 2 * math.sin(2 * math.pi * (h - 9) / 24)
            chuva = 0.0
            if umido[i] and nuvem > 0.72 and rng.random() < 0.18 + 0.25 * conv / 0.18 * (s[i] > 0):
                chuva = float(rng.gamma(1.4, 2.2 + 3 * max(s[i], 0)))
                temp -= 1.5
            umid = float(np.clip(76 - 2.0 * (temp - t_media[i]) + 16 * (nuvem - 0.5)
                                 + (9 if chuva else 0) + rng.normal(0, 3), 32, 100))
            chuva *= FATOR_CHUVA_MES[d.month]
            linhas.append((datetime(d.year, d.month, d.day, h), round(temp, 1), round(nuvem * 100),
                           round(chuva, 1), round(umid)))
    clima = pd.DataFrame(linhas, columns=["time", "temperature_2m", "cloud_cover",
                                          "precipitation", "relative_humidity_2m"])
    idx = pd.DatetimeIndex(clima["time"]) + pd.Timedelta(minutes=30)   # média da hora
    cs = ghi_ceu_claro(posicao_solar(idx))
    c = clima["cloud_cover"].values / 100
    ghi = cs * (1 - 0.75 * c ** 3.4) * rng.normal(1, 0.03, len(c))
    clima["shortwave_radiation"] = np.round(np.clip(ghi, 0, None), 0)
    return clima


# ------------------------------------------------------------------ galeria
PERFIL_GALERIA = {  # ocupação relativa dentro do horário de funcionamento
    "util": {10: .45, 11: .65, 12: .95, 13: 1.0, 14: .8, 15: .72, 16: .75, 17: .85, 18: 1.0, 19: .95, 20: .75, 21: .5},
    "sab": {10: .5, 11: .75, 12: .95, 13: 1.0, 14: 1.0, 15: 1.0, 16: .98, 17: .92, 18: .88, 19: .8, 20: .62, 21: .45},
    "dom": {12: .7, 13: .95, 14: 1.0, 15: 1.0, 16: .95, 17: .85, 18: .7, 19: .5},
}
PERFIL_EV = {  # chegadas relativas por hora (sessões começam na janela do eletroposto)
    "util": {10: .55, 11: .8, 12: 1.15, 13: 1.2, 14: .95, 15: .85, 16: .9, 17: 1.05, 18: 1.25, 19: 1.1, 20: .7},
    "sab": {10: .5, 11: .85, 12: 1.1, 13: 1.2, 14: 1.3, 15: 1.3, 16: 1.25, 17: 1.15, 18: 1.0, 19: .85, 20: .55},
    "dom": {12: 1.0, 13: 1.2, 14: 1.25, 15: 1.2, 16: 1.1, 17: .95, 18: .75, 19: .5},
}
FATOR_DIA_SEMANA = [0.82, 0.85, 0.88, 0.93, 1.06, 1.30, 1.08]


def tipo_dia(info):
    if info["feriado"] or info["dia_semana"] == 6:
        return "dom"
    return "sab" if info["dia_semana"] == 5 else "util"


def preco_base(d):
    p = CFG["preco_base"][0][1]
    for ini, v in CFG["preco_base"]:
        if d >= ini:
            p = v
    return p


def alfa_tarifa(ghi, hora):
    """Mesmo fator α do app: solar alto −12%, solar baixo +4%, ponta +18%."""
    a = 1.0
    if 9 <= hora < 17:
        if ghi > 600:
            a -= 0.12
        elif ghi < 250:
            a += 0.04
    if CFG["ponta"][0] <= hora < CFG["ponta"][1]:
        a += 0.18
    return a


# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clima-real", help="CSV horário da Open-Meteo cobrindo o período + 7 dias")
    args = ap.parse_args()
    os.makedirs(os.path.join(OUT, "supabase"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "_gabarito"), exist_ok=True)
    dias_hist = [CFG["inicio"] + timedelta(days=k) for k in range((CFG["fim"] - CFG["inicio"]).days + 1)]
    dias_fut = [CFG["fim"] + timedelta(days=k + 1) for k in range(CFG["dias_previsao"])]
    todos = dias_hist + dias_fut
    infos = {d: info_dia(d) for d in todos}

    print("clima…", "real: " + args.clima_real if args.clima_real else "simulado")
    clima = carregar_clima_real(args.clima_real, todos) if args.clima_real else gerar_clima(todos)
    clima_hist = clima[clima["time"] < datetime(dias_fut[0].year, dias_fut[0].month, dias_fut[0].day)]
    clima_fut = clima[clima["time"] >= datetime(dias_fut[0].year, dias_fut[0].month, dias_fut[0].day)].copy()

    # previsão Open-Meteo emitida na última leitura: erro cresce com o horizonte
    lead_d = ((clima_fut["time"] - datetime(dias_fut[0].year, dias_fut[0].month, dias_fut[0].day))
              .dt.total_seconds() / 86400).values
    prev = clima_fut.copy()
    # erro de previsão correlacionado no dia (viés do dia + ruído pequeno por hora)
    dia_idx = np.floor(lead_d).astype(int)
    vies = rng.normal(0, 0.5 + 0.25 * np.arange(CFG["dias_previsao"]))
    prev["temperature_2m"] = np.round(prev["temperature_2m"] + vies[dia_idx] + rng.normal(0, 0.4, len(prev)), 1)
    erro_nuvem = np.clip(rng.normal(0, 8 + 4 * lead_d), -45, 45)
    prev["cloud_cover"] = np.clip(prev["cloud_cover"] + erro_nuvem, 0, 100).round()
    fator = (1 - 0.75 * (prev["cloud_cover"] / 100) ** 3.4) / np.maximum(1e-3, 1 - 0.75 * (clima_fut["cloud_cover"] / 100) ** 3.4)
    prev["shortwave_radiation"] = np.round(np.clip(prev["shortwave_radiation"] * fator, 0, 1100), 0)
    prev["precipitation"] = np.round(np.clip(prev["precipitation"] * rng.uniform(0.5, 1.5, len(prev)), 0, None), 1)
    prev.insert(0, "emitida_em", "2026-10-11T23:00:00-03:00")

    # --- grade de 5 min (só o histórico é simulado com equipamentos) -------
    ts = pd.date_range(datetime(2025, 1, 1), datetime(CFG["fim"].year, CFG["fim"].month, CFG["fim"].day, 23, 55), freq="5min")
    N = len(ts)
    print(f"{N} instantes de 5 min…")
    ch = clima_hist.set_index("time")
    hora_idx = ts.floor("h")
    temp = ch["temperature_2m"].reindex(hora_idx).values
    nuvem_h = ch["cloud_cover"].reindex(hora_idx).values / 100
    cosz = posicao_solar(ts)
    cs = ghi_ceu_claro(cosz)
    nuvem5 = np.clip(nuvem_h + rng.normal(0, 0.06, N), 0, 1)
    ghi5 = np.clip(cs * (1 - 0.75 * nuvem5 ** 3.4), 0, None)
    # temperatura suavizada no minuto
    temp5 = pd.Series(temp).rolling(12, min_periods=1, center=True).mean().values

    tcel = temp5 + 0.03 * ghi5
    derate = 1 + CFG["coef_temp_pv"] * (tcel - 25)
    # sujeira nos módulos: perde ~0,12%/dia sem chuva (até 7%); chuva forte lava
    chuva_dia_hist = clima_hist.groupby(clima_hist["time"].dt.date)["precipitation"].sum()
    suj, sujeira = 0.0, {}
    for d in dias_hist:
        suj = 0.0 if chuva_dia_hist.get(d, 0) > 5 else min(0.07, suj + 0.0012)
        sujeira[d] = suj
    # desarme de uma string do inversor: ~5 vezes ao ano, perde 1/3 da geração no dia
    desarme = {d for d in dias_hist if rng.random() < 5 / 365}
    fator_dia = np.array([(1 - sujeira[d]) * (0.66 if d in desarme else 1.0) for d in ts.date])
    pv_src = {k: kwp * f * ghi5 / 1000 * CFG["perdas_sistema"] * derate * fator_dia for k, (kwp, f) in CFG["pv"].items()}
    pv = sum(pv_src.values())

    # movimento do dia (fluxo de pessoas)
    mov_dia = {}
    tmax_dia = {}
    for d in dias_hist:
        inf = infos[d]
        dia_clima = clima_hist[clima_hist["time"].dt.date == d]
        tmax = dia_clima["temperature_2m"].max()
        chuva = dia_clima.loc[dia_clima["time"].dt.hour.between(9, 20), "precipitation"].sum()
        m = FATOR_DIA_SEMANA[inf["dia_semana"]] * inf["fator_comercial"]
        if inf["feriado"]:
            m *= 1.05
        if inf["ponte"]:
            m *= 0.9
        if inf["vespera_feriado"]:
            m *= 1.06
        if inf["ferias_escolares"]:
            m *= 1.07
        if chuva > 3:
            m *= 1.09            # chuva leva gente para dentro do shopping
        # calor leva gente ao shopping climatizado; frio intenso também, menos
        m *= 1 + 0.018 * max(0.0, tmax - 25) + 0.01 * max(0.0, 17 - tmax)
        tmax_dia[d] = tmax
        mov_dia[d] = m * float(rng.lognormal(0, 0.07))

    # operação do condomínio: deriva lenta (ajuste de setpoint, lojas que
    # abrem e fecham, manutenção) + variação própria do dia
    deriva, op_dia = 0.0, {}
    for d in dias_hist:
        deriva = 0.97 * deriva + rng.normal(0, 0.012)
        op_dia[d] = math.exp(deriva) * float(rng.lognormal(0, 0.04))
    # eventos à noite (feira, lançamento, show): ~2 por mês
    eventos_noite = {d: float(rng.uniform(6, 12)) for d in dias_hist if rng.random() < 2 / 30}
    # climatização com defeito (um compressor parado): ~3 episódios/ano de 1–4 dias
    hvac_falha = set()
    for d in dias_hist:
        if rng.random() < 3 / 365:
            for k in range(int(rng.integers(1, 5))):
                hvac_falha.add(d + timedelta(days=k))

    # carga da galeria (kW)
    datas = ts.date
    horas = ts.hour.values
    minutos = ts.minute.values
    galeria = np.zeros(N)
    ocup_arr = np.zeros(N)
    ruido_hora = 0.0
    for i in range(N):
        d = datas[i]
        inf = infos[d]
        h = horas[i]
        perf = PERFIL_GALERIA[tipo_dia(inf)]
        aberto = inf["abre"] <= h < inf["fecha"]
        ruido_hora = 0.9 * ruido_hora + rng.normal(0, 0.03)       # movimento oscila ao longo do dia
        occ = perf.get(h, 0.0) * mov_dia[d] * (1 + ruido_hora) if aberto else 0.0
        ocup_arr[i] = occ
        iluminacao = 6.0 if d >= CFG["retrofit_led"] else 8.5
        carga = 4.6                                   # refrigeração, segurança, TI, bombas
        hm = h + minutos[i] / 60.0
        # pré-abertura: o prédio "acorda" aos poucos, não de uma vez na abertura
        if inf["abre"] - 3 <= hm < inf["abre"]:
            carga += 2.5                              # limpeza, segurança e iluminação parcial (equipe chega ~3 h antes)
        if inf["abre"] - 1.5 <= hm < inf["abre"]:
            carga += 3.5 + 0.5 * iluminacao           # lojistas montando a loja, escadas rolantes em teste, iluminação subindo
        if inf["abre"] - 2 <= hm < inf["fecha"] + 1:
            carga += 1.8                              # estacionamento: ventilação da garagem e iluminação (abre antes, fecha depois)
        if aberto:
            carga += iluminacao + 7.5 * occ           # iluminação + áreas comuns, escadas, elevadores
        if inf["abre"] - 2 <= hm < inf["fecha"]:      # climatização central em estágios de 4 kW
            hv = (1.45 * max(0.0, temp5[i] - 20.5) + 5.0 * ghi5[i] / 1000 + 3.0 * occ) * (0.55 if d in hvac_falha else 1.0)
            if hm < inf["abre"]:
                # pré-resfriamento: tira o calor acumulado da noite antes de abrir (pull-down)
                hv = (2.2 + 1.2 * max(0.0, temp5[i] - 19.0) + 3.0 * ghi5[i] / 1000) * (0.55 if d in hvac_falha else 1.0)
            est = hv / 4.0
            carga += 4.0 * (math.floor(est) + (rng.random() < est - math.floor(est)))
        if d in eventos_noite and 18 <= h < 22:
            carga += eventos_noite[d]
        galeria[i] = carga * op_dia[d]
    galeria *= 1.02 * rng.normal(1, 0.02, N)
    galeria = np.clip(galeria, 2.5, None)

    # ----------------------------------------------- eletroposto + DLM + BESS
    print("sessões OCPP, DLM e BESS…")
    nconn = len(CFG["carregadores"])
    pesos = np.array([f[3] for f in FROTA]); pesos /= pesos.sum()
    # motoristas recorrentes (frequência tipo Zipf) com veículo fixo
    nm = CFG["motoristas"]
    mot_veic = rng.choice(len(FROTA), nm, p=pesos)
    mot_peso = 1 / np.arange(1, nm + 1) ** 0.8; mot_peso /= mot_peso.sum()

    # indisponibilidades dos conectores (dias)
    indisp = np.zeros((nconn, N), bool)
    falhas = []   # (conector, inicio_idx, fim_idx, errorCode, vendor)
    erros = [("GroundFailure", "2087"), ("OtherError", "2091"), ("EVCommunicationError", "1012"), ("PowerMeterFailure", "3004")]
    k = 0
    while k < N:
        for c in range(nconn):
            if rng.random() < 0.012 / 288 * 1.0 and not indisp[c, k]:
                dur = int(np.clip(rng.lognormal(math.log(12 * 12), 0.9), 12, 288 * 4))
                e = erros[rng.integers(len(erros))]
                indisp[c, k:k + dur] = True
                falhas.append((c, k, min(N - 1, k + dur), e[0], e[1]))
        k += 1
    # a Vaga 03 entra em falha na noite de 11/10 — é o estado que o app mostra
    k3 = int(np.searchsorted(ts.values, np.datetime64("2026-10-11T19:40")))
    indisp[2, k3:] = True
    falhas.append((2, k3, N - 1, "OtherError", "2091"))

    soc = 0.5 * CFG["bess_kwh"]
    limite = CFG["demanda_contratada_kw"] * (1 - CFG["margem_dlm"])
    dt = 5 / 60
    t0 = pd.Timestamp(datetime(2025, 1, 1))
    anos = (ts - t0).total_seconds().values / (365.25 * 86400)
    tendencia = CFG["crescimento_ev"] ** anos          # adoção de VE crescendo
    shift_dia = {d: float(clima_hist.loc[(clima_hist["time"].dt.date == d)
                                         & clima_hist["time"].dt.hour.between(8, 16), "cloud_cover"].mean()) > 68
                 for d in dias_hist}

    ativos = [None] * nconn
    sess = []
    mv_rows = []
    aloc_rows = []
    ev_kw = np.zeros(N); disp_ev = np.zeros(N)
    bess_kw = np.zeros(N); soc_arr = np.zeros(N); rede = np.zeros(N)
    registro_wh = np.zeros(nconn)
    perdidas = 0
    tx_id = 100000

    # ruído diário próprio da demanda de recarga
    ruido_ev = {d: float(rng.lognormal(0, 0.12)) for d in dias_hist}
    # DLM sem comunicação com as vagas (OCPP ou rede local caiu): ~10
    # episódios/ano de 1–8 h, e as vagas carregam a plena potência sem teto
    dlm_off = np.zeros(N, bool)
    for k in np.flatnonzero(rng.random(N) < 10 / (365 * 288)):
        dlm_off[k:k + int(rng.integers(12, 97))] = True
    L_med, P_med = 0.0, 0.0      # o DLM e o BESS decidem com a leitura anterior do medidor

    for i in range(N):
        d = datas[i]; h = horas[i]; inf = infos[d]
        tipo = tipo_dia(inf)
        # ---- chegadas
        janela = inf["ep_abre"] <= h < inf["ep_fecha"]
        if janela:
            ghi_h = ghi5[i]
            a = alfa_tarifa(ghi_h, h)
            lam = CFG["lambda_ev"] * tendencia[i] * PERFIL_EV[tipo].get(h, 0) * mov_dia[d] ** 0.9 * ruido_ev[d] * a ** -1.5
            for _ in range(rng.poisson(lam * dt)):
                livres = [c for c in range(nconn) if ativos[c] is None and not indisp[c, i]]
                if not livres:
                    perdidas += 1
                    continue
                c = int(rng.choice(livres))
                m = int(rng.choice(nm, p=mot_peso))
                vi = mot_veic[m]
                nome, cap, pmax, _ = FROTA[vi]
                # dia quente: ar-condicionado do carro gasta mais, chega com menos bateria
                soc0 = float(np.clip(rng.beta(2.2, 3.0) * 0.85 + 0.06 - 0.012 * max(0.0, tmax_dia[d] - 26), 0.05, 0.9))
                alvo = float(rng.choice([0.8, 0.9, 1.0], p=[0.6, 0.2, 0.2]))
                if alvo <= soc0 + 0.05:
                    alvo = min(1.0, soc0 + 0.2)
                med = 55 if (tipo == "util" and 12 <= h < 14) else 80 if tipo == "util" else 95
                perm = float(np.clip(rng.lognormal(math.log(med), 0.45), 20, 260))
                tx_id += 1
                ativos[c] = {
                    "tx": tx_id, "con": c, "mot": m + 1, "veic": vi, "cap": cap, "pmax": min(pmax, CFG["kw_carregador"]),
                    "soc0": soc0, "soc": soc0, "alvo": alvo, "ini": i, "fim_prev": i + int(perm / 5),
                    "kwh": 0.0, "meter_start": registro_wh[c],
                    "preco": round(preco_base(d) * a, 2), "cheio_em": None, "ultimo_kw": None,
                    "interromper": rng.random() < 0.025,
                }
        # ---- demanda solicitada pelas sessões
        req = np.zeros(nconn)
        for c in range(nconn):
            s = ativos[c]
            if s is None:
                continue
            if s["soc"] >= s["alvo"] - 1e-4:
                req[c] = 0
            else:
                taper = 1.0 if s["soc"] < 0.9 else 0.55
                req[c] = s["pmax"] * taper
        ev_req = req.sum()
        L = galeria[i]; P = pv[i]
        # ---- BESS (decide pela última leitura: chega 5 min atrasado nos picos)
        dis = 0.0; carga_bess = 0.0
        energia_disp = max(0.0, (soc - CFG["bess_soc_min"] * CFG["bess_kwh"])) / dt
        espaco = max(0.0, (CFG["bess_kwh"] - soc)) / dt
        liquido = L_med + ev_req - P_med
        if CFG["ponta"][0] <= h < CFG["ponta"][1] and liquido > 0:
            dis = min(CFG["bess_kw"], energia_disp, liquido)
        elif liquido > limite:                          # peak shaving
            dis = min(CFG["bess_kw"], energia_disp, liquido - limite)
        elif shift_dia.get(d, False) and 3 <= h < 6 and soc < 0.9 * CFG["bess_kwh"]:
            carga_bess = min(10.0, espaco)             # load shifting: compra fora de ponta
        # ---- DLM: o que sobra da demanda contratada vai para as vagas
        disponivel = max(0.0, limite - (L_med - P_med - dis + carga_bess))
        disp_ev[i] = min(disponivel, nconn * CFG["kw_carregador"])
        aloc = np.zeros(nconn)
        if ev_req <= disponivel or dlm_off[i]:
            aloc = req.copy()
        else:
            restante = disponivel
            pend = [c for c in range(nconn) if req[c] > 0]
            while pend and restante > 1e-6:
                quota = restante / len(pend)
                novos = []
                for c in pend:
                    falta = req[c] - aloc[c]
                    dar = min(falta, quota)
                    aloc[c] += dar; restante -= dar
                    if req[c] - aloc[c] > 1e-6:
                        novos.append(c)
                if len(novos) == len(pend):
                    break
                pend = novos
        ev = aloc.sum()
        # excedente solar → bateria → exportação
        sobra = P - L - ev + dis
        if sobra > 0 and carga_bess == 0 and dis == 0:
            carga_bess = min(CFG["bess_kw"], sobra, espaco)
        L_med, P_med = L, P
        soc = soc + (carga_bess * 0.95 - dis / 0.95) * dt
        soc = float(np.clip(soc, 0, CFG["bess_kwh"]))
        grid = L + ev + carga_bess - P - dis
        ev_kw[i] = ev; bess_kw[i] = dis - carga_bess; soc_arr[i] = soc; rede[i] = grid

        # ---- avança sessões, MeterValues e alocações
        for c in range(nconn):
            s = ativos[c]
            if s is None:
                continue
            e = aloc[c] * dt
            s["kwh"] += e; registro_wh[c] += e * 1000
            s["soc"] = min(1.0, s["soc"] + e / s["cap"])
            if req[c] > 0 and abs(aloc[c] - req[c]) > 0.3 and (s["ultimo_kw"] is None or abs(aloc[c] - s["ultimo_kw"]) > 0.3):
                aloc_rows.append((s["tx"], round(aloc[c], 2), ts[i]))
            elif s["ultimo_kw"] is not None and abs(aloc[c] - s["ultimo_kw"]) > 0.3 and req[c] > 0:
                aloc_rows.append((s["tx"], round(aloc[c], 2), ts[i]))
            s["ultimo_kw"] = aloc[c]
            if s["soc"] >= s["alvo"] - 1e-4 and s["cheio_em"] is None:
                s["cheio_em"] = i
            v = CFG["tensao_ev"] + rng.normal(0, 2.5)
            mv_rows.append((ts[i] + pd.Timedelta(minutes=5), CFG["carregadores"][c][0], 1, s["tx"],
                            int(round(registro_wh[c])), int(round(aloc[c] * 1000)),
                            round(aloc[c] * 1000 / v, 1), round(v, 1)))
            acabou = i >= s["fim_prev"] or indisp[c, i] or (s["interromper"] and i >= s["ini"] + (s["fim_prev"] - s["ini"]) // 2)
            if acabou:
                motivo = "EVDisconnected" if s["interromper"] else ("Other" if indisp[c, i] else "Local")
                sess.append({**s, "fim": i + 1, "motivo": motivo, "meter_stop": registro_wh[c]})
                ativos[c] = None
    # sessões abertas no fim do histórico são encerradas na última leitura
    for c in range(nconn):
        if ativos[c] is not None:
            s = ativos[c]
            sess.append({**s, "fim": N - 1, "motivo": "Local", "meter_stop": registro_wh[c]})
    print(f"{len(sess)} sessões · {perdidas} chegadas sem vaga livre")

    # --------------------------------------------------------------- saídas
    tz = "-03:00"
    iso = lambda t: pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%S") + tz

    # 1) smart meter GoodWe + inversor (convenção: pmeter > 0 = exportação)
    imp = np.clip(rede, 0, None); exp_ = np.clip(-rede, 0, None)
    pf = np.clip(0.93 + 0.04 * rng.random(N) - 0.03 * (galeria > 30), 0.85, 0.99)
    vfase = 127 + rng.normal(0, 1.4, (3, N))
    ifase = np.abs(rede)[None, :] * 1000 / 3 / vfase / pf * rng.normal(1, 0.04, (3, N))
    # troca do medidor em 10/02/2026: número de série novo e contadores zerados
    k_troca = int(np.searchsorted(ts.values, np.datetime64("2026-02-10T10:00")))
    e_imp = np.cumsum(imp * dt) + 18250.0
    e_exp = np.cumsum(exp_ * dt) + 1210.0
    e_imp[k_troca:] -= e_imp[k_troca - 1]
    e_exp[k_troca:] -= e_exp[k_troca - 1]
    sn = np.where(np.arange(N) < k_troca, "GM3000-PN0187", "GM3000-PN0233")
    med = pd.DataFrame({
        "timestamp": [iso(t) for t in ts + pd.Timedelta(minutes=5)],
        "galeria_id": CFG["galeria_id"],
        "sn_medidor": sn,
        "sn_inversor": "GW50K-SDT-PN0042",
        "pmeter_w": np.round(-rede * 1000).astype(int),
        "e_import_total_kwh": np.round(e_imp, 2),
        "e_export_total_kwh": np.round(e_exp, 2),
        "v_l1": vfase[0].round(1), "v_l2": vfase[1].round(1), "v_l3": vfase[2].round(1),
        "i_l1": ifase[0].round(1), "i_l2": ifase[1].round(1), "i_l3": ifase[2].round(1),
        "fator_potencia": pf.round(3),
        "frequencia_hz": np.round(60 + rng.normal(0, 0.015, N), 3),
        "ppv_w": np.round(pv * 1000).astype(int),
        "ppv_cobertura_w": np.round(pv_src["cobertura"] * 1000).astype(int),
        "ppv_fachada_w": np.round(pv_src["fachada"] * 1000).astype(int),
        "ppv_carport_w": np.round(pv_src["carport"] * 1000).astype(int),
        "pbattery_w": np.round(bess_kw * 1000).astype(int),
        "soc_bateria_pct": np.round(soc_arr / CFG["bess_kwh"] * 100, 1),
        "potencia_disponivel_ev_kw": disp_ev.round(2),   # teto que o DLM calculou
    })
    # O medidor não sabe quanto é galeria e quanto é carro: isso o backend
    # calcula (preparar_dataset.py). Defeitos típicos de telemetria real:
    defeitos = {}
    #  a) lacunas de comunicação do datalogger (~3 por mês, 5 min a 8 h)
    vivo = np.ones(N, bool)
    for k in np.flatnonzero(rng.random(N) < 3 / (30 * 288)):
        vivo[k:k + int(np.clip(rng.lognormal(math.log(6), 1.0), 1, 96))] = False
    #  b) datalogger queimado: 3 dias e meio sem dado em agosto/2025
    a = int(np.searchsorted(ts.values, np.datetime64("2025-08-04T14:10")))
    vivo[a:a + 288 * 3 + 144] = False
    defeitos["medidor_amostras_perdidas"] = int((~vivo).sum())
    #  c) leituras espúrias (tensão zerada / potência absurda) ~0,03%
    esp = np.flatnonzero(vivo & (rng.random(N) < 0.0003))
    med.loc[esp[: len(esp) // 2], ["pmeter_w", "v_l1", "v_l2", "v_l3"]] = 0
    med.loc[esp[len(esp) // 2:], "pmeter_w"] = med.loc[esp[len(esp) // 2:], "pmeter_w"] * 10
    defeitos["medidor_leituras_espurias"] = int(len(esp))
    med = med[vivo]
    #  d) retransmissões duplicadas ~0,3%
    dup = med.sample(frac=0.003, random_state=1)
    defeitos["medidor_duplicadas"] = int(len(dup))
    med = pd.concat([med, dup]).sort_values("timestamp", kind="stable")
    with gzip.open(os.path.join(OUT, "medidor_galeria_5min.csv.gz"), "wt", encoding="utf-8") as f:
        med.to_csv(f, index=False)

    # 2) OCPP
    mv = pd.DataFrame(mv_rows, columns=["timestamp", "charge_point_id", "connector_id", "transaction_id",
                                        "energy_active_import_register_wh", "power_active_import_w",
                                        "current_import_a", "voltage_v"])
    mv["timestamp"] = mv["timestamp"].map(iso)
    mv.insert(4, "context", "Sample.Periodic")
    #  MeterValues perdidos (~1%) e reenviados em dobro (~0,5%) após reconexão
    perde = rng.random(len(mv)) < 0.01
    defeitos["meter_values_perdidos"] = int(perde.sum())
    mv = mv[~perde]
    dup = mv.sample(frac=0.005, random_state=2)
    defeitos["meter_values_duplicados"] = int(len(dup))
    mv = pd.concat([mv, dup]).sort_values(["timestamp", "charge_point_id"], kind="stable")
    with gzip.open(os.path.join(OUT, "ocpp_meter_values.csv.gz"), "wt", encoding="utf-8") as f:
        mv.to_csv(f, index=False)

    tx = []
    eventos = []
    recargas = []
    ev_id = 0
    sem_stop = set(rng.choice(len(sess), int(len(sess) * 0.004), replace=False).tolist())
    defeitos["transacoes_sem_stop"] = len(sem_stop)
    for n_s, s in enumerate(sess):
        cp, evse, vaga = CFG["carregadores"][s["con"]]
        t_ini = ts[s["ini"]]; t_fim = ts[min(s["fim"], N - 1)] + pd.Timedelta(minutes=5 if s["fim"] < N else 0)
        kwh = (s["meter_stop"] - s["meter_start"]) / 1000
        # enum status_recarga do schema.sql: aguardando_plugue → conectando →
        # carregando ⇄ interrompida → concluida (captura só o kWh entregue)
        status = "concluida"
        perdeu_stop = n_s in sem_stop      # carregador perdeu a conexão: o Stop nunca chegou
        tx.append({
            "transaction_id": s["tx"], "charge_point_id": cp, "evse_id": evse, "connector_id": 1,
            "id_tag": f"APP-{s['mot']:05d}", "timestamp_start": iso(t_ini), "meter_start_wh": int(round(s["meter_start"])),
            "timestamp_stop": "" if perdeu_stop else iso(t_fim),
            "meter_stop_wh": "" if perdeu_stop else int(round(s["meter_stop"])),
            "stop_reason": "" if perdeu_stop else s["motivo"],
        })
        recargas.append({
            "id": s["tx"], "carregador_id": s["con"] + 1, "motorista_id": s["mot"] + 1, "veiculo_id": s["mot"],
            "status_recarga": status, "pct_inicial": round(s["soc0"] * 100), "meta_pct": round(s["alvo"] * 100),
            "preco_kwh_aplicado": s["preco"], "kwh_entregue": round(kwh, 3),
            "iniciada_em": iso(t_ini), "finalizada_em": iso(t_fim + pd.Timedelta(minutes=1)), "criado_em": iso(t_ini - pd.Timedelta(minutes=2)),
        })
        marcos = [("aguardando_plugue", t_ini - pd.Timedelta(minutes=2)),
                  ("conectando", t_ini - pd.Timedelta(minutes=1)), ("carregando", t_ini)]
        if s["motivo"] in ("EVDisconnected", "Other"):   # plugue solto ou vaga em falha
            marcos.append(("interrompida", t_fim))
        marcos.append(("concluida", t_fim + pd.Timedelta(minutes=1)))
        for st, t in marcos:
            ev_id += 1
            eventos.append({"id": ev_id, "recarga_id": s["tx"], "status_recarga": st, "ocorrido_em": iso(t)})
    pd.DataFrame(tx).to_csv(os.path.join(OUT, "ocpp_transacoes.csv"), index=False)
    pd.DataFrame(recargas).to_csv(os.path.join(OUT, "supabase", "recargas.csv"), index=False)
    pd.DataFrame(eventos).to_csv(os.path.join(OUT, "supabase", "recarga_eventos.csv"), index=False)

    al = pd.DataFrame(aloc_rows, columns=["recarga_id", "potencia_alocada_kw", "ocorrido_em"])
    al["ocorrido_em"] = al["ocorrido_em"].map(iso)
    al.insert(0, "id", range(1, len(al) + 1))
    al.to_csv(os.path.join(OUT, "supabase", "alocacoes_potencia.csv"), index=False)

    # status notification: transições de cada conector
    stn = []
    for c, (cp, _, _) in enumerate(CFG["carregadores"]):
        stn.append((iso(ts[0]), cp, 1, "Available", "NoError", ""))
    for s in sess:
        cp = CFG["carregadores"][s["con"]][0]
        stn.append((iso(ts[s["ini"]] - pd.Timedelta(minutes=1)), cp, 1, "Preparing", "NoError", ""))
        stn.append((iso(ts[s["ini"]]), cp, 1, "Charging", "NoError", ""))
        if s["cheio_em"] is not None and s["cheio_em"] < s["fim"]:
            stn.append((iso(ts[s["cheio_em"]] + pd.Timedelta(minutes=5)), cp, 1, "SuspendedEV", "NoError", ""))
        fim_t = ts[min(s["fim"], N - 1)]
        stn.append((iso(fim_t + pd.Timedelta(minutes=4)), cp, 1, "Finishing", "NoError", ""))
        if s["motivo"] != "Other":
            stn.append((iso(fim_t + pd.Timedelta(minutes=5)), cp, 1, "Available", "NoError", ""))
    for c, a, b, code, vend in falhas:
        cp = CFG["carregadores"][c][0]
        stn.append((iso(ts[a]), cp, 1, "Faulted", code, vend))
        if b < N - 1:
            stn.append((iso(ts[b]), cp, 1, "Available", "NoError", ""))
    stn = pd.DataFrame(stn, columns=["timestamp", "charge_point_id", "connector_id", "status", "error_code", "vendor_error_code"])
    stn.sort_values("timestamp").to_csv(os.path.join(OUT, "ocpp_status_notification.csv"), index=False)

    # tabelas de apoio do ER, para a importação fechar as chaves estrangeiras.
    # Pessoas fictícias: sem CPF, e-mail em domínio reservado (example.com).
    sup = os.path.join(OUT, "supabase")
    pd.DataFrame([{"id": 1, "cep": "01310-200", "logradouro": "Avenida Paulista", "numero": "1578",
                   "complemento": "", "bairro": "Bela Vista", "cidade": "São Paulo", "uf": "SP",
                   "latitude": CFG["lat"], "longitude": CFG["lon"]}]).to_csv(os.path.join(sup, "enderecos.csv"), index=False)
    usuarios = [{"id": 1, "nome": "Gestor Galeria Pátio Norte (fictício)", "email": "gestor.patio.norte@example.com",
                 "senha_hash": "", "cpf": "", "telefone": "", "criado_em": "2024-12-01T09:00:00-03:00"}]
    usuarios += [{"id": m + 2, "nome": f"Motorista {m + 1:04d} (fictício)", "email": f"motorista{m + 1:04d}@example.com",
                  "senha_hash": "", "cpf": "", "telefone": "", "criado_em": "2024-12-15T09:00:00-03:00"} for m in range(nm)]
    pd.DataFrame(usuarios).to_csv(os.path.join(sup, "usuarios.csv"), index=False)
    pd.DataFrame([{"id": CFG["galeria_id"], "endereco_id": 1, "anfitriao_id": 1, "nome": CFG["galeria"],
                   "demanda_contratada_kw": CFG["demanda_contratada_kw"], "criado_em": "2024-12-01T09:00:00-03:00"}]
                 ).to_csv(os.path.join(sup, "galerias.csv"), index=False)
    pd.DataFrame([{"codigo": "GW7K-HCA-20", "potencia_kw": 7.0, "descricao": "GoodWe HCA G2 7 kW · monofásico · Tipo 2"}]
                 ).to_csv(os.path.join(sup, "modelos_carregador.csv"), index=False)
    pd.DataFrame([{"id": c + 1, "galeria_id": CFG["galeria_id"], "modelo_codigo": "GW7K-HCA-20", "numero_serie": sn,
                   "nome": vaga, "preco_kwh": 2.19, "publicado": c != 2, "criado_em": "2024-12-20T09:00:00-03:00"}
                  for c, (sn, _, vaga) in enumerate(CFG["carregadores"])]).to_csv(os.path.join(sup, "carregadores.csv"), index=False)

    # veículos dos motoristas (tabela veiculos do ER)
    pd.DataFrame({
        "id": np.arange(1, nm + 1), "motorista_id": np.arange(2, nm + 2),
        "marca": [FROTA[v][0].split(" ")[0] for v in mot_veic],
        "modelo": [" ".join(FROTA[v][0].split(" ")[1:]) for v in mot_veic],
        "apelido": "", "capacidade_bateria_kwh": [FROTA[v][1] for v in mot_veic],
    }).to_csv(os.path.join(OUT, "supabase", "veiculos.csv"), index=False)

    # leituras_energia (ER): 1 leitura a cada 15 min, média do intervalo
    m15 = pd.DataFrame({"t": ts, "disp": disp_ev, "tot": galeria + ev_kw, "vivo": vivo}).set_index("t").resample("15min").mean()
    m15 = m15[m15["vivo"] == 1]          # sem leitura do medidor, o backend não grava
    le = pd.DataFrame({
        "id": np.arange(1, len(m15) + 1), "galeria_id": CFG["galeria_id"],
        "potencia_disponivel_ev_kw": m15["disp"].round(2).values,
        "potencia_total_utilizada_kw": m15["tot"].round(2).values,
        "ocorrido_em": [iso(t + pd.Timedelta(minutes=15)) for t in m15.index],
    })
    le.to_csv(os.path.join(OUT, "supabase", "leituras_energia.csv"), index=False)

    # clima (estação com falhas pontuais: ~0,3% das horas sem leitura)
    ch_out = clima_hist.copy()
    if not args.clima_real:
        falha = rng.random(len(ch_out)) < 0.003
        ch_out.loc[falha, ["temperature_2m", "shortwave_radiation", "relative_humidity_2m"]] = np.nan
        defeitos["clima_horas_faltando"] = int(falha.sum())
        ch_out["relative_humidity_2m"] = ch_out["relative_humidity_2m"].round().astype("Int64")   # inteiro, vazio onde faltou
    ch_out["time"] = ch_out["time"].map(iso)
    ch_out.to_csv(os.path.join(OUT, "clima_horario.csv"), index=False)
    prev["time"] = prev["time"].map(iso)
    prev.to_csv(os.path.join(OUT, "previsao_clima_open_meteo.csv"), index=False)

    # ------------------------------------------------ gabarito horário (verdade)
    print("gabarito horário…")
    base5 = pd.DataFrame({
        "t": ts, "ev_kwh": ev_kw * dt, "galeria_kwh": galeria * dt, "pv_kwh": pv * dt,
        "rede_kw": rede, "ev_kw": ev_kw,
        "vagas_operando": (~indisp).sum(axis=0),
    }).set_index("t")
    hr = pd.DataFrame({
        "galeria_kw_pico": pd.Series(galeria, index=ts).resample("15min").mean().resample("h").max(),
        "ev_kwh": base5["ev_kwh"].resample("h").sum(),
        "galeria_kwh": base5["galeria_kwh"].resample("h").sum(),
        "solar_kwh": base5["pv_kwh"].resample("h").sum(),
        "demanda_rede_pico_kw": base5["rede_kw"].resample("15min").mean().resample("h").max(),
        "ev_pico_kw": base5["ev_kw"].resample("15min").mean().resample("h").max(),
        "vagas_operando": base5["vagas_operando"].resample("h").min(),
    })
    sess_df = pd.DataFrame({"t": [ts[s["ini"]].floor("h") for s in sess]})
    hr["sessoes_iniciadas"] = sess_df.groupby("t").size().reindex(hr.index, fill_value=0)
    hr["dlm_offline"] = pd.Series(dlm_off, index=ts).resample("h").max().astype(int)
    hr = hr.rename_axis("timestamp").reset_index()
    hr["timestamp"] = hr["timestamp"].map(iso)
    num = ["ev_kwh", "galeria_kwh", "solar_kwh", "demanda_rede_pico_kw", "ev_pico_kw", "galeria_kw_pico"]
    hr[num] = hr[num].round(3)
    hr.to_csv(os.path.join(OUT, "_gabarito", "horario_verdade.csv"), index=False)
    eventos_reg = {
        "retrofit_led": CFG["retrofit_led"].isoformat(),
        "troca_medidor": "2026-02-10T10:00",
        "eventos_noturnos": sorted(d.isoformat() for d in eventos_noite),
        "climatizacao_com_defeito": sorted(d.isoformat() for d in hvac_falha),
        "desarme_inversor": sorted(d.isoformat() for d in desarme),
    }
    import json
    with open(os.path.join(OUT, "_gabarito", "defeitos_e_eventos.json"), "w") as f:
        json.dump({"defeitos_injetados": defeitos, "eventos": eventos_reg}, f, ensure_ascii=False, indent=1)

    # calendário dos 7 dias futuros (o app precisa dele para prever)
    pd.DataFrame([infos[d] for d in dias_fut]).to_csv(os.path.join(OUT, "calendario_previsao.csv"), index=False)

    # ---------------------------------------------------------------- resumo
    dia = hr.assign(d=pd.to_datetime(hr["timestamp"].str[:10])).groupby("d")[["ev_kwh", "galeria_kwh", "solar_kwh"]].sum()
    print(dia.describe().round(1))
    horas_ep = sum(infos[d]["ep_fecha"] - infos[d]["ep_abre"] for d in dias_hist)
    print("sessões/dia (média):", round(len(sess) / len(dias_hist), 1), "· chegadas sem vaga:", perdidas)
    print("utilização das vagas (energia):", round(dia["ev_kwh"].sum() / (nconn * CFG["kw_carregador"] * horas_ep) * 100, 1), "%")
    q = pd.Series(rede, index=ts).resample("15min").mean()
    print("pico de demanda da rede (kW):", round(q.max(), 1), "· intervalos de 15 min acima de 55 kW:", int((q > CFG["demanda_contratada_kw"]).sum()))
    print("PV kWh/kWp/ano:", round(dia["solar_kwh"].mean() * 365 / 67.2))
    print("defeitos:", defeitos)


if __name__ == "__main__":
    main()
