-- Registro das cobranças feitas pela Edge Function `pagamentos` (Mercado Pago).
--
-- Tabela própria do protótipo: guarda cada pré-autorização, captura e split
-- 90/10 sem depender de recargas/usuarios. Quando o schema completo
-- (banco-de-dados/schema.sql) for aplicado, estes dados migram para
-- `pagamentos` e `repasses`.

create table if not exists public.transacoes_pagamento (
  id               bigint generated always as identity primary key,
  gateway_id       text not null unique,          -- id do pagamento no Mercado Pago (ou cred-... para créditos)
  recarga_ref      text,                          -- referência da recarga no app
  metodo           text check (metodo in ('cartao', 'pix', 'creditos')),
  status           text not null,                 -- pending | authorized | approved | cancelled | refunded
  valor_autorizado numeric(10,2),                 -- reservado na largada
  valor_total      numeric(10,2),                 -- capturado no fim (kWh entregues)
  valor_anfitriao  numeric(10,2),                 -- 90% para a galeria
  taxa_plataforma  numeric(10,2),                 -- 10% GoodWe
  processado_em    timestamptz,
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now(),
  check (valor_total is null or valor_autorizado is null or valor_total <= valor_autorizado)
);

-- só a Edge Function (service_role) lê e grava; o app nunca acessa direto
alter table public.transacoes_pagamento enable row level security;
