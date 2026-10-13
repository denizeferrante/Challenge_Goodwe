-- Assistente de IA do ChargeGrid (chatbot do motorista + Síndico Virtual)
-- Base de conhecimento do RAG com pgvector, memória das conversas e log de auditoria.

create extension if not exists vector;

-- ---------------------------------------------------------------- RAG
-- Trechos dos PDFs do HCA G2, documentos do desafio e FAQ do app
-- (carregados por supabase/scripts/ingerir_conhecimento.py)
create table if not exists ia_conhecimento (
  id          bigserial primary key,
  fonte       text not null,            -- 'pdf' | 'docx' | 'faq' | 'web'
  titulo      text,
  conteudo    text not null,
  publico     text not null default 'todos' check (publico in ('todos', 'motorista', 'sindico')),
  embedding   vector(1536) not null,    -- text-embedding-3-small
  criado_em   timestamptz not null default now()
);
create index if not exists ia_conhecimento_embedding_idx
  on ia_conhecimento using hnsw (embedding vector_cosine_ops);

-- busca semântica (equivalente ao vector_store.similarity_search da Sprint 03)
create or replace function buscar_conhecimento(
  consulta vector(1536), papel text, k int default 4, limiar float default 0.25
) returns table (titulo text, fonte text, conteudo text, similaridade float)
language sql stable as $$
  select titulo, fonte, conteudo, 1 - (embedding <=> consulta) as similaridade
  from ia_conhecimento
  where publico in ('todos', papel)
    and 1 - (embedding <=> consulta) >= limiar
  order by embedding <=> consulta
  limit k;
$$;

-- ---------------------------------------------------------------- conversas
-- A memória do grafo fica no checkpointer Postgres do LangGraph (tabelas
-- checkpoints*, criadas pelo próprio PostgresSaver.setup()). Esta tabela é o
-- log legível por turno, no lugar do conversas_chatbot.jsonl da Sprint 03.
create table if not exists ia_turnos (
  id              bigserial primary key,
  thread_id       text not null,
  usuario_id      uuid,
  papel           text not null check (papel in ('motorista', 'sindico')),
  pergunta        text not null,
  resposta        text not null,
  guardrail       text not null default 'ok',   -- ok | injection | lgpd | saida_juridico | saida_financeiro
  fora_de_escopo  boolean not null default false,
  ferramentas     text[] not null default '{}', -- ferramentas chamadas no turno
  fontes          text[] not null default '{}', -- títulos dos trechos do RAG usados
  modelo          text,
  latencia_ms     int,
  tokens_entrada  int,
  tokens_saida    int,
  criado_em       timestamptz not null default now()
);
create index if not exists ia_turnos_thread_idx on ia_turnos (thread_id, criado_em);

-- ações sugeridas pelo Síndico Virtual: nunca executadas sem confirmação do gestor
create table if not exists ia_acoes_sugeridas (
  id           bigserial primary key,
  thread_id    text not null,
  tipo         text not null,     -- ajustar_tarifa | agendar_compra_rede | reiniciar_vaga | ...
  detalhe      jsonb not null,
  status       text not null default 'pendente' check (status in ('pendente', 'confirmada', 'descartada')),
  criado_em    timestamptz not null default now(),
  decidido_em  timestamptz
);

-- LGPD: só o próprio usuário lê os seus turnos; a Edge Function usa a service role
alter table ia_turnos enable row level security;
create policy ia_turnos_proprio on ia_turnos for select using (auth.uid() = usuario_id);
alter table ia_acoes_sugeridas enable row level security;
alter table ia_conhecimento enable row level security;
create policy ia_conhecimento_leitura on ia_conhecimento for select using (true);
