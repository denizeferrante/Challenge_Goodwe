# Banco de dados

Modelo de dados do ChargeGrid: PostgreSQL, destinado ao Supabase. O diagrama em
`diagrama-er-supabase.mermaid` renderiza direto no GitHub — é só abrir o arquivo.

## Decisões de modelagem

**Papel não é coluna, é relação.** Não existe campo `tipo_usuario`. Quem é anfitrião de
uma `galeria` é anfitrião; quem aparece como motorista em uma `recarga` é motorista. A
mesma pessoa pode ser os dois — que é exatamente o caso do condômino que aluga a
própria vaga.

**`recargas` é a tabela-pivô.** Dela penduram o histórico de estados
(`recarga_eventos`), os ajustes de potência do DLM (`alocacoes_potencia`), o
`pagamento` e a `avaliacao`. Guardar as transições em tabela separada, em vez de só o
status corrente, é o que permite auditar uma sessão interrompida e cobrar apenas os
kWh entregues.

**Preço é congelado na sessão.** `recargas.preco_kwh_aplicado` guarda a tarifa travada
no plug-in, separada de `carregadores.preco_kwh`, que o anfitrião pode mudar a qualquer
momento. Sem isso, uma alteração de preço reescreveria o valor de sessões já em curso.

**O split 90/10 é explícito em `pagamentos`.** `valor_total`, `taxa_plataforma` e
`valor_anfitriao` são colunas, não um cálculo feito na hora da consulta. `repasses`
registra o pagamento efetivo ao anfitrião, ligado à `conta_repasse` (Pix ou conta
bancária) que ele cadastrou.

**Medição da galeria e alocação da sessão são coisas diferentes.**
`leituras_energia` guarda a leitura da galeria inteira (potência disponível para EV e
potência total utilizada); `alocacoes_potencia` guarda quanto o DLM concedeu a cada
recarga. Uma responde "a galeria está dentro da demanda contratada?", a outra responde
"por que a minha carga caiu para 14 kW?".

**`modelos_carregador` é tabela, não enum.** Potência e descrição do HCA G2 e dos
demais modelos vivem em dados, porque o catálogo GoodWe muda sem que o esquema precise
mudar.

**Sem reserva.** Não há tabela de reservas: `disponibilidades` define as janelas em que
o carregador aceita uso, e o atendimento é por ordem de chegada.

## Tabelas

15 no total.

| Domínio | Tabelas |
|---|---|
| Pessoas e locais | `usuarios`, `enderecos`, `galerias` |
| Equipamento | `modelos_carregador`, `carregadores`, `disponibilidades` |
| Veículo e sessão | `veiculos`, `recargas`, `recarga_eventos` |
| Energia | `leituras_energia`, `alocacoes_potencia` |
| Dinheiro | `pagamentos`, `contas_repasse`, `repasses` |
| Feedback | `avaliacoes` |

## Estado

Modelado e revisado. O `schema.sql` desta pasta e o `diagrama-er-supabase.mermaid` são a
referência do ER. A base simulada de `../inteligencia/dados/supabase/` segue as colunas do
mermaid e foi importada com sucesso num PostgreSQL 16 local (chaves estrangeiras, enum e
`check`s respeitados; ver `../inteligencia/supabase/er_minimo_para_teste.sql`).

No Supabase já estão as migrations da IA e dos pagamentos (`../supabase/migrations/`).
As 15 tabelas do ER ainda não foram migradas para lá, e o app ainda não lê nem grava
nelas.
