"""
Variáveis do machine learning do ChargeGrid (mesma lógica das aulas de SERS).

Monta, a partir do dataset_horario.csv, a tabela com nomes em português usada
no notebook ChargeGrid_ML.ipynb, no Orange e no app. O motor do app
(app/src/ml/previsao-motor.js) calcula exatamente estas colunas, na mesma
ordem; testar_paridade_js.py confere as duas pontas.
"""

import numpy as np
import pandas as pd

CLIMA = ["temperatura_c", "umidade_pct", "nuvens_pct", "irradiancia_w_m2", "chuva_mm"]
CALENDARIO = ["hora", "dia_semana", "feriado", "fator_comercial"]

X_GALERIA = CLIMA + CALENDARIO + ["galeria_aberta", "media_4sem_galeria_kwh"]
X_EV = CLIMA + CALENDARIO + ["eletroposto_aberto", "vagas_operando", "media_4sem_ev_kwh"]
# Eletroposto no app: o Random Forest aprende o FORMATO do dia (hora ÷ nível recente) e o
# nível vem da média das 4 semanas. Árvore não prevê acima do que viu no treino, e a frota
# cresce ~45% ao ano: prevendo o valor bruto, o modelo ficaria sempre para trás.
X_EV_FORMATO = [c for c in X_EV if c != "media_4sem_ev_kwh"]
NIVEL_MIN_EV = 0.3

X_NIVEL = CLIMA + CALENDARIO + ["galeria_aberta", "eletroposto_aberto", "vagas_operando",
                                "media_4sem_galeria_kwh", "media_4sem_ev_kwh"]

# Classes do nível de demanda na rede (pico de 15 min da hora), em kW.
# Alta começa em 35 kW: ~72% do teto operacional de 48,4 kW (55 kW contratados − 12%).
LIMITES_NIVEL = (20.0, 35.0)
CLASSES_NIVEL = ["Baixa", "Média", "Alta"]


def media_4sem(y: pd.Series) -> pd.Series:
    """Mesma hora nas 4 semanas anteriores (168, 336, 504 e 672 h atrás).
    É histórico já medido: não usa o valor da própria hora prevista."""
    return pd.concat([y.shift(k) for k in (168, 336, 504, 672)], axis=1).mean(axis=1)


def nivel_ev(tab: pd.DataFrame) -> pd.Series:
    """Nível recente do eletroposto: média das "médias de 4 semanas" nas últimas 168 horas
    (inclui a hora atual), em kWh por hora; mínimo de 0,3. É a escala do modelo relativo.
    tab precisa ser contínua no tempo (uma linha por hora)."""
    return tab["media_4sem_ev_kwh"].rolling(168, min_periods=24).mean().clip(lower=NIVEL_MIN_EV)


def nivel_demanda(kw):
    a, b = LIMITES_NIVEL
    return np.where(kw >= b, "Alta", np.where(kw >= a, "Média", "Baixa"))


def montar(df: pd.DataFrame) -> pd.DataFrame:
    """df: dataset_horario.csv (contínuo, ordenado por hora).
    Devolve a tabela da aula: entradas, alvos e data_hora."""
    t = pd.to_datetime(df["timestamp"].astype(str).str[:19])
    hora = t.dt.hour
    out = pd.DataFrame({
        "data_hora": t,
        "temperatura_c": df["temperature_2m"],
        "umidade_pct": df["relative_humidity_2m"],
        "nuvens_pct": df["cloud_cover"],
        "irradiancia_w_m2": df["shortwave_radiation"],
        "chuva_mm": df["precipitation"],
        "hora": hora,
        "dia_semana": df["dia_semana"],          # 0 = segunda … 6 = domingo
        "feriado": df["feriado"],
        "fator_comercial": df["fator_comercial"],  # 1 = dia comum; >1 data de movimento alto
        "galeria_aberta": ((hora >= df["abre"]) & (hora < df["fecha"])).astype(int),
        "eletroposto_aberto": ((hora >= df["ep_abre"]) & (hora < df["ep_fecha"])).astype(int),
        "vagas_operando": df["vagas_operando"],
        # sem arredondar: o app (JS) arredonda .5 de outro jeito que o pandas
        "media_4sem_galeria_kwh": media_4sem(df["galeria_kwh"]),
        "media_4sem_ev_kwh": media_4sem(df["ev_kwh"]),
        # alvos
        "galeria_kwh": df["galeria_kwh"],
        "ev_kwh": df["ev_kwh"],
        "demanda_rede_kw": df["demanda_rede_pico_kw"],
        "solar_kwh": df["solar_kwh"],
    }, index=df.index)
    out["nivel_demanda"] = pd.Series(nivel_demanda(out["demanda_rede_kw"].fillna(-1)), index=df.index)
    out.loc[out["demanda_rede_kw"].isna(), "nivel_demanda"] = np.nan
    return out
