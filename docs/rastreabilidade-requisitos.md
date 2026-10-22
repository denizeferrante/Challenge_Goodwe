# Rastreabilidade dos requisitos — Sprint 4

Cruza cada requisito do documento **Mapeamento de Requisitos conforme Nano Engenharia de
Software** ([`docs/requisitos/`](requisitos/Mapeamento-de-Requisitos-Nano-Engenharia-de-Software.docx)) com o que existe no repositório ao fim da Sprint 4.

**Legenda:** ✅ atendido · 🟡 parcial (o porquê está na coluna de evidência) · ⏳ não atendido

**Resumo:** dos 40 requisitos (20 RF, 5 RNF, 15 RN), **26 estão atendidos, 13 parciais e
1 não atendido** (RN003). Os parciais concentram-se em dois pontos: a lógica que ainda
roda no cliente em vez do Supabase e a integração física (Modbus→OCPP, API SEMS).

---

## Requisitos funcionais

| ID | Requisito | Status | Evidência no repositório |
|---|---|---|---|
| RF001 | Controle dinâmico de carga (DLM) | 🟡 | `dlmAgora()` em `app/src/app.js`: teto = 55 kW − pico da edificação − 12%, repartido entre as vagas em carga; tela da sessão e detalhe da vaga mostram a potência repartida. Base simulada aplica o DLM com 5 min de atraso e perdas de comunicação (`inteligencia/gerar_base_simulada.py`). Executa no cliente e só informa: a sessão simulada não reduz a potência quando o DLM limita |
| RF002 | Middleware Modbus → OCPP 1.6 | 🟡 | Dados e telas usam `StartTransaction`, `StopTransaction`, `MeterValues`, `StatusNotification` (`inteligencia/dados/ocpp_*.csv`, detalhe da vaga). O gateway que traduz o Modbus do HCA G2 não foi implementado |
| RF003 | Estimativa de tempo e valor antes da sessão | ✅ | Telas *Confirmar recarga* e *Forma de pagamento* (modos tempo, kWh e km): ex. 20,0 kWh · 2h56 · R$ 43,80 |
| RF004 | Sessão → dados estruturados e inteligência acionável | ✅ | ETL `inteligencia/preparar_dataset.py` → `dataset_horario.csv`; tabelas `recargas` e `recarga_eventos` (`inteligencia/dados/supabase/`); previsão e alertas no app |
| RF005 | Liberação de carga via app / QR Code | ✅ | Fluxo *Já estou no eletroposto* → leitura de QR (vaga e série OCPP) → pagamento → carga liberada |
| RF006 | Registro estruturado da sessão (usuário, potência, kWh, duração, custo) | 🟡 | Modelado em `recargas` (+ `preco_kwh_aplicado`, `kwh_entregue`, início/fim) no ER; 3.274 sessões simuladas no formato; `transacoes_pagamento` grava cada cobrança pela Edge Function. O app ainda guarda a sessão em memória |
| RF007 | Dashboard financeiro B2B (diário, semanal, mensal) | 🟡 | Tela *Financeiro*: resultado do dia, receita bruta, economia, custo de rede, faturamento por dia/mês/ano, repasse Pix. Falta a visão semanal |
| RF008 | Chatbot Síndico Virtual (NLP/RAG) | ✅ | `supabase/functions/assistente/` (LangGraph.js + OpenAI + RAG pgvector + memória + guardrails); `app/src/ia/assistente.js`; 12/12 testes offline |
| RF009 | KPIs ESG: CO₂ evitado, árvores, ranking | 🟡 | Telas *Impacto* (motorista e galeria), CO₂ no recibo, árvores equivalentes. Ranking entre usuários não implementado; fatores de CO₂ divergem entre telas |
| RF010 | ML para ocupação e tarifação dinâmica (ponta, solar, demanda, Open-Meteo) | ✅ | `inteligencia/ChargeGrid_ML.ipynb`: Random Forest (galeria e eletroposto), classificador de demanda, K-Means; clima no formato Open-Meteo; exportado para `app/src/ml/` |
| RF011 | Supabase como backend | 🟡 | Edge Functions `assistente` e `pagamentos`, migrations `supabase/migrations/`, segredos em `supabase secrets`, RLS. ER completo, Realtime e Auth ainda não ligados ao app |
| RF012 | Simulação de vagas antes de instalar | ✅ | Simulador de vagas (gestor) e viabilidade (prospect): kWp por superfície, irradiação de SP, baterias, vagas, faturamento |
| RF013 | Mapa com status em tempo real e rota GPS | ✅ | *Encontrar recarga*: pontos com status (livre, ocupado com previsão de liberação, falha), distância e rota no Google Maps. Status vem de dados simulados |
| RF014 | Histórico global (casa + eletropostos) | ✅ | Aba *Carga*: filtros Eletroposto / Casa / Todos, kWh e gasto do mês |
| RF015 | IA calcula o preço por kWh (ponta, demanda, solar) | 🟡 | `alfa()` em `app/src/app.js`; tela *Tarifa* mostra "como a IA chega ao fator α". O preço cobrado do motorista ainda vem fixo do cadastro do ponto, sem α |
| RF016 | Síndico traduz telemetria em insights | ✅ | Abertura do Síndico com resumo do dia e previsão; alertas com selo "previsão"; explicação do DLM e do load shifting |
| RF017 | Personas Gestor e Cliente final | ✅ | Motorista, gestor com solução e gestor prospect |
| RF018 | Tarifa base + fator α (solar alto, ponta) com ponto ótimo por derivadas | 🟡 | α implementado: solar alto −12%, nublado +4%, ponta +18%, demanda concorrente exibida. A otimização do preço por derivada (lucro máximo) não foi implementada — α é regra por faixas |
| RF019 | Eletropostos favoritos | ✅ | Filtro *Favoritos* no mapa; contagem e notificação de vaga livre no perfil |
| RF020 | Perfil do veículo (modelo, bateria útil, kWh/km) | ✅ | *Perfil → Meu veículo elétrico*: Renault Megane E-Tech · 60 kWh · 0,17 kWh/km · Tipo 2; usado na estimativa por km |

## Requisitos não funcionais

| ID | Requisito | Status | Evidência |
|---|---|---|---|
| RNF001 | Cores do app = LEDs do hardware | ✅ | Tokens `status-available` azul, `status-charging` verde, `status-fault` vermelho (`design-system/tokens.json`); firmware com RGB puro equivalente |
| RNF002 | Multiplataforma Android e iOS | 🟡 | App web responsivo que roda no navegador do celular (Android e iOS) e offline em arquivo único; não é app nativo nem PWA instalável |
| RNF003 | Gestão de segredos | ✅ | `.env` fora do Git (`.env.example`), chaves da OpenAI e do Mercado Pago só em `supabase secrets`, app só com chave anon (substituída no build local), RLS em `transacoes_pagamento` e tabelas da IA |
| RNF004 | Interface externa OCPP 1.6 / ANEEL 1.000/2021 | 🟡 | Vocabulário OCPP 1.6 em dados e telas; tarifa travada e cobrança só do entregue (transparência). Sem endpoint OCPP real para CPO |
| RNF005 | Textos do simulador sobre HVAC | 🟡 | Simulador usa 15%–25% de redução de HVAC e exibe "Estimativa preliminar e paramétrica… Não constitui garantia de economia". Os três textos completos do requisito não estão literalmente na tela |

## Regras de negócio

| ID | Regra | Status | Evidência |
|---|---|---|---|
| RN001 | Hierarquia de despacho (EVs → bateria → edificação) | ✅ | Regra do rateio: com a galeria aberta o sol atende primeiro o eletroposto (até 80%), depois a galeria; a bateria atende primeiro o eletroposto |
| RN002 | Tarifa congelada no plug-in | ✅ | `recargas.preco_kwh_aplicado`; "Tarifa travada" na sessão e no recibo. No app, o preço é gravado na liberação da carga, logo após o plugue físico |
| RN003 | Prioridade para bateria crítica (SOC < 10%) | ⏳ | Não implementado: o DLM reparte igualmente entre as vagas em carga |
| RN004 | Proteção contra ultrapassagem de demanda | ✅ | Teto operacional de 48,4 kW; alerta de demanda perto do teto; pico previsto vs. teto na tela Previsão |
| RN005 | % de energia dedicada à edificação | ✅ | Reserva configurável no simulador e no rateio (`simEvPct`, `repEv`; sugestão 80/20) |
| RN006 | Parceiros de eficiência para LEED/AQUA | ✅ | Telas *Parceiros GoodWe* e *Certificação* (créditos LEED e AQUA) |
| RN007 | Load shifting preditivo | ✅ | Banner e decisões do Síndico: carregar bateria de madrugada, puxar recarga para o sol, pré-resfriar; só recomenda com economia ≥ R$ 3/dia |
| RN008 | Previsão (Open-Meteo) para planejar, medição (SEMS Plus) para faturar | 🟡 | Previsão usa o clima no formato Open-Meteo; a regra aparece na tela Tarifa. Faturamento pela medição SEMS depende da integração com a API SEMS |
| RN009 | Dimensionamento físico de vagas | ✅ | Fórmula com fator 0,72 e 7 kW por vaga, % de reserva configurável (`app/src/app.js`, simulador) |
| RN010 | Comercial como funil para o residencial | ✅ | Persona prospect → simulador → parceiros; aba *Casa* (Smart Home) para o motorista |
| RN011 | CO₂ e árvores tangíveis para gestor e motorista | ✅ | Impacto da galeria (marketing) e Meu impacto (motorista) |
| RN012 | Uso parcial da geração na edificação | ✅ | Rateio configurável |
| RN013 | Integração do ecossistema GoodWe | 🟡 | HCA G2, smart meter, inversor, BESS e SEMS modelados nos dados e no app; integração real com a API SEMS pendente |
| RN014 | Gestor define base, IA opera | ✅ | Tela *Tarifa*: base editável + α automático |
| RN015 | Pagamento em duas fases | ✅ | `supabase/functions/pagamentos/`: autorizar (`capture:false` / QR Pix) e capturar parcial / estornar sobra; testado no fluxo: R$ 43,80 autorizados, R$ 8,76 capturados |

## Pontos do desafio fora dos RF/RN

| Ponto | Status | Evidência |
|---|---|---|
| Limite de cartões RFID (Pilar III) | ✅ | Identificação e pagamento por app/QR Code, sem cartão físico |
| Arquitetura funcional (data flow) | ✅ | `README.md` seção 3 e `docs/arquitetura-da-solucao.png` |
| Gestão e estrutura de dados | ✅ | `banco-de-dados/` (ER de 15 tabelas) e dicionário de dados em `inteligencia/README.md` |
