"""
Calendário da Galeria Pátio Norte (São Paulo/SP).

Feriados nacionais, estadual (SP) e municipal (São Paulo), datas comerciais
que mexem com o movimento de shopping e férias escolares. É usado tanto pelo
gerador da base simulada quanto pelo modelo de previsão — o mesmo calendário
dos dois lados, como seria em produção.
"""

from datetime import date, timedelta


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def _n_esimo_domingo(ano, mes, n):
    d = date(ano, mes, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d + timedelta(weeks=n - 1)


def feriados(ano: int) -> dict:
    """{data: nome}. Comércio de shopping abre em horário reduzido nesses dias.
    Carnaval não entra: é ponto facultativo e está em datas_comerciais()."""
    p = pascoa(ano)
    f = {
        date(ano, 1, 1): "Confraternização Universal",
        date(ano, 1, 25): "Aniversário de São Paulo",
        p - timedelta(days=2): "Sexta-feira Santa",
        date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho",
        p + timedelta(days=60): "Corpus Christi",
        date(ano, 7, 9): "Revolução Constitucionalista",
        date(ano, 9, 7): "Independência do Brasil",
        date(ano, 10, 12): "Nossa Senhora Aparecida",
        date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República",
        date(ano, 11, 20): "Dia da Consciência Negra",
        date(ano, 12, 25): "Natal",
    }
    return f


def datas_comerciais(ano: int) -> dict:
    """{data: (nome, fator de movimento)} — datas em que o shopping enche."""
    maes = _n_esimo_domingo(ano, 5, 2)
    pais = _n_esimo_domingo(ano, 8, 2)
    nov1 = date(ano, 11, 1)
    # Black Friday = sexta depois da 4ª quinta de novembro
    d = nov1
    quintas = 0
    while True:
        if d.weekday() == 3:
            quintas += 1
            if quintas == 4:
                break
        d += timedelta(days=1)
    bf = d + timedelta(days=1)
    p = pascoa(ano)
    c = {
        # Carnaval é ponto facultativo: o shopping abre no horário normal, com
        # movimento menor (parte da cidade viaja)
        p - timedelta(days=48): ("Carnaval (ponto facultativo)", 0.85),
        p - timedelta(days=47): ("Carnaval (ponto facultativo)", 0.80),
        maes - timedelta(days=1): ("Véspera do Dia das Mães", 1.30),
        maes: ("Dia das Mães", 1.15),
        date(ano, 6, 11): ("Véspera do Dia dos Namorados", 1.15),
        date(ano, 6, 12): ("Dia dos Namorados", 1.25),
        pais - timedelta(days=1): ("Véspera do Dia dos Pais", 1.20),
        pais: ("Dia dos Pais", 1.10),
        date(ano, 10, 11): ("Véspera do Dia das Crianças", 1.20),
        date(ano, 10, 12): ("Dia das Crianças", 1.25),
        bf: ("Black Friday", 1.45),
        bf + timedelta(days=1): ("Sábado da Black Friday", 1.25),
        date(ano, 12, 24): ("Véspera de Natal", 1.20),
        date(ano, 12, 31): ("Véspera de Ano-Novo", 0.75),
    }
    # temporada de Natal: rampa de 1/dez a 23/dez
    for k in range(1, 24):
        dd = date(ano, 12, k)
        if dd not in c:
            c[dd] = ("Temporada de Natal", 1.0 + 0.25 * k / 23)
    return c


def ferias_escolares(d: date) -> bool:
    return (d.month == 1) or (d.month == 7 and d.day <= 31) or (d.month == 12 and d.day >= 18) \
        or (d.month == 2 and d.day <= 2)


def info_dia(d: date) -> dict:
    fer = feriados(d.year)
    com = datas_comerciais(d.year)
    eh_feriado = d in fer
    amanha, ontem = d + timedelta(days=1), d - timedelta(days=1)
    fer_amanha = amanha in feriados(amanha.year)
    fer_ontem = ontem in feriados(ontem.year)
    # ponte: dia útil espremido entre feriado e fim de semana
    ponte = (not eh_feriado and d.weekday() < 5 and (
        (d.weekday() == 0 and fer_amanha) or (d.weekday() == 4 and fer_ontem)))
    domingo_ou_feriado = eh_feriado or d.weekday() == 6
    return {
        "data": d,
        "dia_semana": d.weekday(),              # 0 = segunda ... 6 = domingo
        "feriado": int(eh_feriado),
        "nome_feriado": fer.get(d, ""),
        "vespera_feriado": int(fer_amanha and not eh_feriado),
        "ponte": int(ponte),
        "data_comercial": com[d][0] if d in com else "",
        "fator_comercial": com[d][1] if d in com else 1.0,
        "ferias_escolares": int(ferias_escolares(d)),
        # horário do shopping / janela do eletroposto
        "abre": 12 if domingo_ou_feriado else 10,
        "fecha": 20 if domingo_ou_feriado else 22,
        "ep_abre": 12 if domingo_ou_feriado else 10,
        "ep_fecha": 20 if domingo_ou_feriado else 21,
    }
