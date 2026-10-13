-- =====================================================================
-- ChargeGrid · tabelas propostas para a previsão de demanda (ML)
-- PostgreSQL / Supabase — PROPOSTA, complementa diagrama-er-supabase.mermaid
--
-- O ER atual cobre sessão, pagamento e uma leitura agregada da galeria
-- (leituras_energia). Para treinar e servir o modelo faltam: a medição
-- bruta do smart meter, os MeterValues OCPP, o clima, as previsões e os
-- alertas do Síndico Virtual. Nenhuma tabela existente é alterada.
--
-- Os CSVs de inteligencia/dados/ já estão nestes formatos.
-- Validar nomes e tipos com quem mantém o Supabase antes de aplicar.
-- =====================================================================

-- Smart meter GoodWe + inversor + BESS (como chega do SEMS), 5 min
create table if not exists medicoes_medidor (
    id                         bigint generated always as identity primary key,
    galeria_id                 bigint not null references galerias(id),
    sn_medidor                 text   not null,
    sn_inversor                text,
    ocorrido_em                timestamptz not null,
    pmeter_w                   integer not null,          -- > 0 exportação, < 0 importação
    e_import_total_kwh         numeric(12,2),
    e_export_total_kwh         numeric(12,2),
    v_l1 numeric(5,1), v_l2 numeric(5,1), v_l3 numeric(5,1),
    i_l1 numeric(6,1), i_l2 numeric(6,1), i_l3 numeric(6,1),
    fator_potencia             numeric(4,3),
    frequencia_hz              numeric(6,3),
    ppv_w                      integer,                   -- geração total
    ppv_cobertura_w            integer,
    ppv_fachada_w              integer,
    ppv_carport_w              integer,
    pbattery_w                 integer,                   -- > 0 descarga
    soc_bateria_pct            numeric(4,1),
    consumo_galeria_kw         numeric(8,2),              -- calculado pelo backend
    consumo_ev_kw              numeric(8,2),              -- soma das vagas (OCPP)
    potencia_disponivel_ev_kw  numeric(8,2),              -- teto do DLM no instante
    unique (galeria_id, ocorrido_em)
);
create index if not exists medicoes_medidor_tempo on medicoes_medidor (galeria_id, ocorrido_em desc);

-- MeterValues OCPP 1.6 (Sample.Periodic) por transação
create table if not exists ocpp_meter_values (
    id                                bigint generated always as identity primary key,
    recarga_id                        bigint not null references recargas(id),
    carregador_id                     bigint not null references carregadores(id),
    connector_id                      smallint not null default 1,
    ocorrido_em                       timestamptz not null,
    context                           text not null default 'Sample.Periodic',
    energy_active_import_register_wh  bigint  not null,
    power_active_import_w             integer,
    current_import_a                  numeric(5,1),
    voltage_v                         numeric(5,1)
);
create index if not exists ocpp_mv_recarga on ocpp_meter_values (recarga_id, ocorrido_em);

-- StatusNotification OCPP (disponibilidade e falhas das vagas)
create table if not exists ocpp_status_notification (
    id                 bigint generated always as identity primary key,
    carregador_id      bigint not null references carregadores(id),
    connector_id       smallint not null default 1,
    ocorrido_em        timestamptz not null,
    status             text not null,      -- Available, Preparing, Charging, SuspendedEV, Finishing, Faulted…
    error_code         text not null default 'NoError',
    vendor_error_code  text
);

-- Clima horário (Open-Meteo): observado (fonte = 'historico') ou previsto
create table if not exists clima_horario (
    id                    bigint generated always as identity primary key,
    galeria_id            bigint not null references galerias(id),
    fonte                 text   not null check (fonte in ('historico', 'previsao')),
    emitida_em            timestamptz,     -- só para previsão
    ocorrido_em           timestamptz not null,
    temperature_2m        numeric(4,1),
    shortwave_radiation   numeric(6,1),    -- W/m², irradiância global
    cloud_cover           smallint,
    precipitation         numeric(5,1),
    relative_humidity_2m  smallint,
    unique (galeria_id, fonte, emitida_em, ocorrido_em)
);

-- Saída do modelo: uma linha por hora prevista, por alvo
create table if not exists previsoes (
    id               bigint generated always as identity primary key,
    galeria_id       bigint not null references galerias(id),
    alvo             text   not null check (alvo in ('ev', 'galeria', 'solar', 'rede')),
    gerada_em        timestamptz not null,       -- quando o modelo rodou
    hora_prevista    timestamptz not null,
    kwh_previsto     numeric(8,3) not null,
    kwh_p10          numeric(8,3),               -- faixa de 80%
    kwh_p90          numeric(8,3),
    versao_modelo    text not null,              -- ex.: '2026-10-11'
    cenario          jsonb not null default '{}', -- ex.: {"vagas": 3}
    unique (galeria_id, alvo, gerada_em, hora_prevista)
);
create index if not exists previsoes_consulta on previsoes (galeria_id, alvo, hora_prevista);

-- Alertas do Síndico Virtual gerados a partir das previsões
create table if not exists alertas_sindico (
    id               bigint generated always as identity primary key,
    galeria_id       bigint not null references galerias(id),
    tipo             text not null,   -- dem (demanda contratada), cap (vagas lotadas), sol (load shifting), exc (excedente), cal (calendário)
    severidade       text not null check (severidade in ('critico', 'atencao', 'info')),
    dia_referencia   date not null,
    titulo           text not null,
    resumo           text,
    regra            text,
    acao             text,
    gerado_em        timestamptz not null default now(),
    resolvido_em     timestamptz
);

-- Leitura no app pelo Realtime
alter publication supabase_realtime add table previsoes, alertas_sindico;
