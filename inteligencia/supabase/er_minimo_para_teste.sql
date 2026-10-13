-- Esquema mínimo derivado do diagrama-er-supabase.mermaid, SÓ para testar a importação dos CSVs
-- num PostgreSQL local (o Supabase real já tem estas tabelas). Ordem: este arquivo, depois previsao_schema.sql.
create type status_recarga as enum ('aguardando_plugue','conectando','carregando','interrompida','concluida','cancelada');
create table usuarios (id bigint primary key, nome text not null, email text unique not null, senha_hash text, cpf text unique, telefone text, criado_em timestamptz);
create table enderecos (id bigint primary key, cep text, logradouro text, numero text, complemento text, bairro text, cidade text, uf text, latitude numeric, longitude numeric);
create table galerias (id bigint primary key, endereco_id bigint references enderecos(id), anfitriao_id bigint references usuarios(id), nome text, demanda_contratada_kw numeric, criado_em timestamptz);
create table modelos_carregador (codigo text primary key, potencia_kw numeric, descricao text);
create table carregadores (id bigint primary key, galeria_id bigint references galerias(id), modelo_codigo text references modelos_carregador(codigo), numero_serie text unique, nome text, preco_kwh numeric(8,2), publicado boolean, criado_em timestamptz);
create table veiculos (id bigint primary key, motorista_id bigint references usuarios(id), marca text, modelo text, apelido text, capacidade_bateria_kwh numeric(5,1) check (capacidade_bateria_kwh > 0));
create table recargas (id bigint primary key, carregador_id bigint not null references carregadores(id), motorista_id bigint not null references usuarios(id), veiculo_id bigint references veiculos(id), status_recarga status_recarga not null, pct_inicial smallint check (pct_inicial between 0 and 100), meta_pct smallint check (meta_pct between 1 and 100), preco_kwh_aplicado numeric(8,2) not null, kwh_entregue numeric(8,3) check (kwh_entregue >= 0), iniciada_em timestamptz, finalizada_em timestamptz, criado_em timestamptz, check (meta_pct > pct_inicial), check (finalizada_em >= iniciada_em));
create table recarga_eventos (id bigint primary key, recarga_id bigint references recargas(id), status_recarga status_recarga not null, ocorrido_em timestamptz);
create table leituras_energia (id bigint primary key, galeria_id bigint references galerias(id), potencia_disponivel_ev_kw numeric, potencia_total_utilizada_kw numeric, ocorrido_em timestamptz);
create table alocacoes_potencia (id bigint primary key, recarga_id bigint references recargas(id), potencia_alocada_kw numeric, ocorrido_em timestamptz);
create publication supabase_realtime;
