#!/usr/bin/env python3
"""
Baixa o clima REAL horário da Av. Paulista (Open-Meteo, arquivo histórico
ERA5, sem chave de API) para trocar o clima simulado da base.

    python3 baixar_clima_real.py                     # 01/01/2025 a 18/10/2026
    python3 gerar_base_simulada.py --clima-real dados/clima_real_open_meteo.csv
    python3 preparar_dataset.py && python3 executar_notebook.py ChargeGrid_ML.ipynb

Precisa de internet (o ambiente de nuvem usado para gerar a base bloqueia a
Open-Meteo; rode no seu computador). O arquivo histórico tem alguns dias de
atraso: se a data final ainda não estiver disponível, ajuste --fim.
"""
import argparse
import json
import os
import urllib.request

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
VARS = ["temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "shortwave_radiation"]

ap = argparse.ArgumentParser()
ap.add_argument("--inicio", default="2025-01-01")
ap.add_argument("--fim", default="2026-10-18")
ap.add_argument("--lat", type=float, default=-23.561414)
ap.add_argument("--lon", type=float, default=-46.655881)
a = ap.parse_args()

url = ("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s&start_date=%s&end_date=%s"
       "&hourly=%s&timezone=America%%2FSao_Paulo" % (a.lat, a.lon, a.inicio, a.fim, ",".join(VARS)))
print("baixando", url)
with urllib.request.urlopen(url, timeout=120) as r:
    d = json.load(r)["hourly"]
df = pd.DataFrame(d)
saida = os.path.join(BASE, "dados", "clima_real_open_meteo.csv")
df.to_csv(saida, index=False)
print(len(df), "horas →", saida)
