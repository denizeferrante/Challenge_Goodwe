# Inteligência — previsão de demanda com machine learning

Previsão, hora a hora e para os próximos 7 dias, de:

- **kWh entregues pelo eletroposto** (as 4 vagas HCA G2 da Galeria Pátio Norte);
- **kWh consumidos pelo condomínio da galeria** (áreas comuns e climatização
  central, sem os carregadores).

A previsão considera temperatura, irradiância (insolação), nebulosidade, chuva,
umidade, dia da semana, feriado, véspera, ponte, datas comerciais, férias
escolares, horário de funcionamento, vagas operando e o histórico das semanas
anteriores. O app consulta a previsão do dia e da semana, e o **Síndico Virtual**
transforma o resultado em alertas (RF010, RF016, UC06, UC08, RN007, RN008).

> **A base é simulada.** Não há medição real da galeria. Os arquivos imitam o
> que chegaria do smart meter GoodWe (via inversor/SEMS) e dos carregadores pelo
> OCPP 1.6, com os parâmetros que o próprio app usa e os defeitos que telemetria
> real tem. Com a medição real, troca-se a entrada; ETL, modelo e app continuam
> os mesmos.

## Rodar

```bash
pip install numpy pandas scikit-learn matplotlib
python3 gerar_base_simulada.py      # ~1 min · arquivos brutos em dados/ (com defeitos)
python3 preparar_dataset.py         # ~20 s  · ETL: limpa os brutos e monta dataset_horario.csv
python3 construir_notebook.py       # monta ChargeGrid_ML.ipynb (textos e código)
python3 executar_notebook.py ChargeGrid_ML.ipynb   # ~1 min · treina, avalia e exporta para o app
python3 testar_paridade_js.py       # confere que o app reproduz o Python (requer node)
cd ../app && python3 build.py       # remonta o app com o modelo novo
```

**Clima real.** O gerador aceita o clima medido no lugar do simulado.
`baixar_clima_real.py` baixa o histórico horário da Open-Meteo (ERA5, sem chave
de API) para a Av. Paulista. Rode no seu computador, porque o ambiente que gerou
a base bloqueia a Open-Meteo:

```bash
python3 baixar_clima_real.py
python3 gerar_base_simulada.py --clima-real dados/clima_real_open_meteo.csv
```

O notebook também pode ser aberto e rodado no Jupyter ou no Colab, célula a
célula; `executar_notebook.py` só existe para rodá-lo sem Jupyter instalado.

As sementes são fixas: rodar de novo gera exatamente a mesma base e os mesmos modelos.

## Estrutura

Um único caminho, de ponta a ponta: **dados → ETL → notebook → app**.

```
inteligencia/
├── calendario.py              feriados de SP, datas comerciais, Carnaval (ponto facultativo), férias
├── gerar_base_simulada.py     1. simulador: clima, condomínio, PV, BESS, DLM, sessões OCPP, defeitos
├── baixar_clima_real.py          (opcional) clima real da Open-Meteo no lugar do simulado
├── preparar_dataset.py        2. ETL: arquivos brutos → dataset_horario.csv + qualidade_dados.json
├── variaveis.py               3. variáveis do modelo (espelhadas em app/src/ml/previsao-motor.js)
├── construir_notebook.py      4. escreve o ChargeGrid_ML.ipynb (roteiro das aulas de SERS)
├── ChargeGrid_ML.ipynb           o machine learning: classificação, regressão, clustering, semana prevista
├── executar_notebook.py          roda o notebook sem Jupyter
├── exportar_app.py            5. chamado pelo notebook: grava app/src/ml/previsao-dados.js
├── testar_paridade_js.py      6. Python × JS, mesma previsão (inclui valores ausentes)
├── dados/                     base (ver dicionário abaixo)
│   ├── _gabarito/                a verdade por hora e os defeitos injetados (só existe por ser simulada)
│   ├── treino_teste/             divisão temporal 80/20 usada no notebook
│   └── supabase/                 a base nas tabelas do ER
├── orange/                    as mesmas tabelas para o fluxo do Orange (File → Test and Score)
├── resultados/paridade_js.json   amostra que o teste de paridade compara
└── supabase/
    ├── previsao_schema.sql        tabelas novas propostas para o Supabase
    └── er_minimo_para_teste.sql   ER do mermaid, só para testar a importação localmente
```

## A base simulada

Período **01/01/2025 a 11/10/2026** (649 dias), mais a previsão do tempo emitida
para 12 a 18/10/2026.

| Parâmetro | Valor | De onde vem |
|---|---|---|
| Galeria | Pátio Norte, Av. Paulista 1578, 2.400 m² | app (`sites`, simulador) |
| O que o medidor mede | **condomínio**: áreas comuns, climatização central, iluminação, estacionamento, vagas. As lojas têm medidor próprio da Enel | premissa explícita (ver Limitações) |
| Geração | 43,2 kWp cobertura · 9,6 kWp fachada BIPV · 14,4 kWp carport | Painel do app |
| BESS | 30 kWh · 15 kW, descarga na ponta (17h–21h), mínimo 10% | Painel do app |
| Vagas | 4 × GoodWe HCA G2 7 kW, mesmos números de série do app | `CHARGERS_INICIAIS` |
| Demanda contratada | 55 kW, DLM com margem de 12% (teto operacional de 48,4 kW) | `dlmAgora()` |
| Tarifa | base R$ 1,99 → 2,09 → 2,19 com fator α (solar −12%, nublado +4%, ponta +18%) | app (tarifa) |
| Horário | seg–sáb 10h–22h (eletroposto até 21h); domingo e feriado 12h–20h | app (horários) |

### Como cada parte foi calibrada

| Parte | Resultado na base | Referência |
|---|---|---|
| Clima | máx./mín. médias 27/20 °C em janeiro e 22/13 °C em julho; chuva ~290 mm em janeiro e ~35 mm em agosto | normais aproximadas do INMET para São Paulo (1991–2020) |
| Geração | 1.330 kWh/kWp por ano, contando fachada, sujeira e desarmes | faixa típica de São Paulo |
| Condomínio | 443 kWh/dia em média (~67 kWh/m² por ano), mais no verão | coerente para áreas comuns; baixo para um prédio inteiro |
| Eletroposto | ~5 sessões por dia e 15% de utilização (energia entregue ÷ capacidade no horário aberto), subindo de ~12% para ~20% com a frota | carregador público AC costuma ter utilização baixa; um estudo no Reino Unido acha mediana abaixo de 5% |
| Sessão | ~9 kWh e ~95 min em média | recarga de quem está no shopping |

### O que torna a base parecida com dado real

**Condomínio.** Carga base de 4,6 kW, iluminação, áreas comuns proporcionais ao
movimento e climatização central em **estágios de 4 kW** (compressores ligando e
desligando). O prédio **acorda antes de abrir**, como um real: equipe, limpeza e
iluminação parcial a partir de 3 h antes; garagem (ventilação e iluminação) e
**pré-resfriamento** da climatização a partir de 2 h antes, puxando o calor
acumulado da noite; lojistas e escadas rolantes na última 1 h 30. Em dia útil
(abre às 10h) o consumo já está em ~17 kWh às 8h e ~22 kWh às 9h, sem o degrau
artificial na abertura. Além disso:

- uma **deriva lenta** da operação (ajuste de setpoint, lojas que abrem e fecham);
- variação própria de cada dia;
- oscilação do movimento ao longo do dia;
- cerca de 2 **eventos noturnos** por mês (+6 a 12 kW);
- cerca de 3 episódios por ano de **climatização com defeito**;
- a **troca da iluminação por LED em 16/03/2026**, uma mudança estrutural que o
  modelo precisa absorver pelo histórico.

**Solar.** Sujeira que se acumula entre chuvas (até 7%) e cerca de 5 desarmes
por ano de uma string do inversor.

**Eletroposto.** Chegadas em processo de Poisson, com:

- perfil horário por tipo de dia e crescimento da procura de cerca de 45% ao ano;
- elasticidade ao preço: o desconto α do sol atrai sessões;
- frota brasileira típica (BYD Dolphin Mini, Dolphin, Song Plus, GWM Ora 03,
  Volvo EX30 etc.), com bateria e carregador de bordo aproximados;
- em dia quente, o carro chega com menos bateria;
- sem reserva: quem chega com as vagas ocupadas vai embora;
- falhas aleatórias dos conectores. A Vaga 03 entra em falha na noite de 11/10,
  que é o estado mostrado no app.

**DLM e bateria imperfeitos.** Os dois decidem pela **leitura anterior do
medidor** (5 min de atraso), e o DLM perde a comunicação com as vagas cerca de 10
vezes por ano, de 1 a 8 h. Mesmo assim, a rede nunca passou dos 55 kW
contratados na base. Com esta galeria e 4 vagas de 7 kW, isso é raro de fato, e
forçar o caso seria inventar dado. Há 93 horas com pico de 15 min acima do
teto operacional de 48,4 kW, que são as situações em que o DLM precisa agir.

**Defeitos de telemetria nos arquivos brutos** (contagem em `_gabarito/defeitos_e_eventos.json`):

| Defeito | Quantidade | Tratamento no ETL |
|---|---|---|
| Lacunas do datalogger (5 min a 8 h, ~3 por mês) e 3,5 dias sem dado em agosto/2025 | 1.542 amostras | hora com menos de 10 das 12 amostras fica sem alvo (149 h) |
| Leituras espúrias (tensão zerada, potência ×10) | 61 | filtro de tensão + salto contra a mediana dos vizinhos |
| Retransmissões duplicadas do medidor | 556 | mantém a primeira |
| Troca do medidor em 10/02/2026 (novo nº de série, contadores zerados) | 1 | energia sai das potências, não dos contadores |
| MeterValues perdidos / duplicados | 596 / 294 | registrador interpolado / deduplicação |
| StopTransaction que nunca chegou | 13 | sessão fechada no último MeterValue |
| Horas sem clima na estação | 46 | interpolação até 3 h |

O ETL reconstrói o consumo da galeria por balanço de potência (importação −
exportação + solar + bateria − vagas), porque o medidor não separa galeria de
carro. Comparado com o gabarito, ele erra 0,005% no total da galeria e 0,04% no
das vagas, e acerta 99,6% das horas de vagas operando (`dados/qualidade_dados.json`).

### Dicionário de dados (`dados/`)

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `medidor_galeria_5min.csv.gz` | 185.926 | Smart meter GoodWe GM3000 + inversor + BESS a cada 5 min: `pmeter_w` (**> 0 = exportação**, convenção adotada), energia importada/exportada acumulada, tensão e corrente por fase, FP, frequência, `ppv_w` por superfície, `pbattery_w` (> 0 = descarga), `soc_bateria_pct`, `potencia_disponivel_ev_kw` (teto do DLM). **Com lacunas, duplicatas e leituras espúrias** |
| `ocpp_meter_values.csv.gz` | 59.044 | `MeterValues` (`Sample.Periodic`, 5 min): `Energy.Active.Import.Register` (Wh), `Power.Active.Import` (W), `Current.Import` (A), `Voltage` (V). Com perdas e duplicatas |
| `ocpp_transacoes.csv` | 3.274 | `StartTransaction` / `StopTransaction` (`stop_reason` vazio onde o Stop não chegou) |
| `ocpp_status_notification.csv` | 13.785 | `StatusNotification`: `Available`, `Preparing`, `Charging`, `SuspendedEV`, `Finishing`, `Faulted` + `error_code` e `vendor_error_code` |
| `clima_horario.csv` | 15.576 | Histórico com os nomes de variável da API Open-Meteo. Com horas vazias |
| `previsao_clima_open_meteo.csv` | 168 | Previsão emitida em 11/10 às 23h para 12 a 18/10 (é o que o app usa) |
| `calendario_previsao.csv` | 7 | Calendário dos dias previstos (12/10 é feriado e Dia das Crianças) |
| `dataset_horario.csv` | 15.576 | **Saída do ETL, tabela do modelo**: alvos (`ev_kwh`, `galeria_kwh`, vazios sem cobertura), `solar_kwh`, picos de 15 min, sessões, vagas operando, clima e calendário |
| `qualidade_dados.json` | — | Relatório do ETL |
| `supabase/*.csv` | — | Tabelas do ER (`recargas` 3.274, `recarga_eventos` 13.176, `alocacoes_potencia` 1.556, `leituras_energia` 61.746, `veiculos` 900) + tabelas de apoio (`usuarios`, `enderecos`, `galerias`, `modelos_carregador`, `carregadores`), com pessoas fictícias sem CPF e e-mail em `example.com` |

Todos os horários estão em `America/Sao_Paulo` (`-03:00`). Os arquivos de
`supabase/` seguem as colunas do `diagrama-er-supabase.mermaid` (por exemplo,
`status_recarga` e `carregadores.galeria_id`, que diferem do `schema.sql` mais
antigo da raiz). A importação foi testada num PostgreSQL 16, com chaves
estrangeiras, enum e `check`s respeitados. As retransmissões duplicadas do
medidor são barradas pela chave única de `medicoes_medidor`. Para repetir o
teste, use `supabase/er_minimo_para_teste.sql` e depois `supabase/previsao_schema.sql`.

## O modelo (`ChargeGrid_ML.ipynb`)

O notebook segue o roteiro das atividades de aula (CP2 de SERS e
`MachineLearning_DadosEnergia`): análise exploratória, divisão **temporal 80/20**
(treino até 06/06/2026, teste até 11/10/2026, sem embaralhar), comparação de
Regressão Linear/Logística, KNN (k = 5) e Random Forest, e a escolha justificada
pelas métricas no teste. As variáveis estão em `variaveis.py`: clima, hora, dia
da semana, feriado, fator comercial, horário de funcionamento, vagas operando e a
média da mesma hora nas 4 semanas anteriores.

| Parte | Pergunta | Escolhido | Resultado no teste |
|---|---|---|---|
| 1 · Classificação | A hora terá demanda Baixa (< 20 kW), Média ou Alta (≥ 35 kW) na rede? | Random Forest com `class_weight="balanced"` | F1 macro 0,656; nenhuma hora Alta prevista como Baixa (recall da Alta 0,354; o resto vira Média) |
| 2.1 · Regressão linear | Quais variáveis explicam a galeria? | Modelo com seleção de variáveis | R² 0,9369 → 0,9384 |
| 2.2 · Galeria (kWh/h) | Quanto o condomínio consome em cada hora? | Random Forest regularizado (60 árvores, profundidade 10, 83× menor que o de 200 árvores) | R² 0,961; MAE 1,27 kWh; erro do total diário **6,1%** (média das 4 semanas: 8,4%) |
| 2.3 · Eletroposto (kWh/h) | Quanto as vagas entregam em cada hora? | Random Forest **relativo ao nível**: aprende o formato do dia e multiplica pelo nível das últimas semanas, porque árvore não extrapola o crescimento da frota | R² 0,360; MAE 1,96 kWh; erro diário **37,1%** (média: 39,9%); na semana 14,0% (média: 12,4%) |
| 3 · Clustering | Que tipos de dia existem? | K-Means, k = 3 (cotovelo + silhouette 0,326) | Dia quente e ensolarado (181), Dia de muita recarga (127), Dia ameno ou nublado (295) |
| 4 · Aplicação | Como fica a semana de 12 a 18/10? | os modelos acima, retreinados com todo o histórico | exportados para o app |

**Leitura dos números.**

- **Galeria.** Previsível: o horário de funcionamento, a temperatura e o
  histórico explicam quase tudo. Os 6% de erro no dia ficam dentro do típico
  para previsão de consumo de prédio comercial.
- **Eletroposto.** Com cerca de 5 sessões por dia, o total diário é quase sorte:
  nenhum método erra menos de ~37%. O modelo ganha da média por hora e por dia; na
  soma da semana a média simples é melhor. O valor da previsão nas vagas está na
  curva hora a hora e no planejamento de rede e bateria, não no total exato.
- **Demanda Alta.** É rara (7% das horas), por isso o modelo balanceado: ele
  troca acurácia por não deixar passar hora crítica como Baixa.
- **Clima medido no teste.** As métricas usam o clima medido; na operação entra
  a previsão do tempo, que tem erro, então o erro real será um pouco maior.

## No app

A Parte 4 do notebook chama `exportar_app.py`, que gera
`app/src/ml/previsao-dados.js` com as árvores dos dois Random Forest, a classe
de demanda prevista para cada hora da semana, os perfis do K-Means, as últimas
semanas medidas (`null` onde faltou medição), a previsão do tempo, o calendário
e as métricas do teste. O motor `app/src/ml/previsao-motor.js` roda a inferência **no
próprio app**, com as mesmas regras de dado ausente do Python;
`testar_paridade_js.py` garante diferença máxima de 0,0001 kWh, inclusive em
linhas com valores ausentes.

- **Início do gestor:** card "Previsão · IA" com o dia, o perfil do dia (K-Means) e o alerta principal.
- **Tela Previsão:**
  - **Previsão de demanda separada** para galeria e eletroposto (dia e semana):
    cada um com o total, a faixa de 80%, o pico e a comparação com a semana
    passada.
  - **Consumo × geração por horário**: no mesmo gráfico, o consumo previsto da
    galeria e do eletroposto, a geração solar prevista e a bateria (acima do
    zero quando entrega, abaixo quando carrega), com a ponta sombreada.
  - *Dia* ou *Semana*, com galeria e eletroposto na mesma tela: **energia necessária**
    (galeria + vagas, faixa de 80%) e **de onde ela vem**, em blocos separados
    para a galeria e para o eletroposto (solar, bateria e rede de cada um; em
    cada hora as fontes são divididas na proporção do consumo), mais o que é
    exportado e o custo estimado.
  - **Armazenamento do sol**: quanto do sol que sobra cabe nas baterias
    instaladas (2 módulos de 15 kWh, 27 kWh úteis), a hora em que enchem, o que
    vai para a rede e quantos módulos seriam precisos para cobrir a ponta.
  - Gráfico hora a hora por fonte (solar, bateria, rede) ou por consumidor, com
    a geração solar e a faixa de ponta.
  - **Banner de load shifting** (dia): aparece quando as baterias não enchem com o
    sol antes da ponta (pouca irradiação ou capacidade sobrando) e a compra
    compensa; mostra quanto comprar das 03h às 06h (tarifa fora de ponta), o uso
    na ponta das 17h às 21h, a economia do dia e um botão para programar.
  - **Load-shifting**: o balanço do dia é refeito com a carga deslocada e a
    recomendação só aparece quando economiza pelo menos R$ 3 no dia. São três
    tipos: carregar a bateria com a rede entre 03h e 06h, puxar a recarga dos
    carros da ponta para as horas de sol sobrando (metade do possível, via
    tarifa) e pré-resfriar a galeria em dia quente. O botão programa o plano.
  - **Síndico Virtual lendo o gráfico**, logo abaixo do hora a hora: explica
    quanto sol sobra e quanto vai para a rede, quanto a rede entrega na ponta, e
    avalia duas decisões — comprar energia de madrugada e ampliar a bateria
    (+30, +60 e +90 kWh, refazendo a semana prevista com a bateria maior;
    premissa de R$ 2.500/kWh instalado e potência 0,5C), com economia anual,
    investimento, retorno e o preço do kWh a partir do qual a ampliação compensa.
  - "Por que esse número": efeito de cada fator, por contrafactual no modelo.
  - Pico previsto na rede contra o teto do DLM, com a bateria achatando a ponta.
  - Horas de demanda Alta previstas pelo classificador e alertas do Síndico.
  - Simulação de cenário (temperatura, Vaga 03 reparada).
  - Como o modelo acerta.
- **Síndico Virtual:** a abertura traz a previsão do dia e os alertas, e
  responde perguntas sobre a previsão.
- **Alertas:** os da previsão entram na lista com o selo "previsão". São eles:
  demanda perto do teto, horas de demanda Alta, vagas lotadas, load-shifting
  recomendado (com a economia da semana), sol sobrando com vagas ociosas,
  feriado e data comercial.

**Balanço de energia.** O motor do app segue a **regra de negócio do rateio**
como **prioridade**: com a galeria aberta, o sol atende primeiro o eletroposto,
até 80% da geração; o restante vai para a galeria; só o que ainda sobrar carrega a
bateria ou é exportado (nunca se compra da rede com sol sobrando). A bateria
atende primeiro o eletroposto.
Com a galeria fechada, o sol atende quem estiver consumindo. No mais, usa a lógica
de despacho do simulador: o sol atende o consumo da hora, a sobra carrega a bateria
(30 kWh, 15 kW, mínimo 10%, eficiência de 95%) e o resto é exportado; na ponta a
bateria descarrega achatando o pico; o que falta vem da rede. Tarifas usadas:
ponta R$ 1,50/kWh, fora de ponta R$ 0,85/kWh e crédito estimado de R$ 0,60 por
kWh exportado. Com 30 kWh de bateria, a sobra solar costuma encher a bateria
antes da ponta mesmo em dia nublado, por isso a pré-carga pela rede raramente
compensa nesta galeria.

A integração com o ESP32 (`hwFind`, `hwSet`, `hwPoll`, LED e botão físico) não
foi alterada.

## Limitações que continuam

- **Escopo do medidor.** Assumimos que o medidor mede o condomínio (áreas comuns
  e climatização central), não as lojas. Isso precisa ser confirmado com a
  equipe. Se for o prédio inteiro, o consumo deveria ser algumas vezes maior.
- **Comportamento.** Os efeitos de Black Friday, calor, chuva e preço sobre o
  movimento são premissas, não medições. O modelo aprende essas premissas.
- **Ultrapassagem da contratada.** Não há caso real na base, então o alerta de
  risco de multa só foi validado por cenário (temperatura +5 °C) e por horas
  acima do teto operacional.
- **Números fixos do protótipo.** O "Resumo de hoje" do protótipo (por exemplo,
  246,8 kWh vendidos) é demonstração fixa e não conversa com esta base, que dá
  cerca de 60 kWh/dia nas vagas.
- **Dados reais.** O caminho para eles é um export do SEMS de uma planta
  comercial real, pedido na mentoria GoodWe, mais o clima real por
  `baixar_clima_real.py`.

## Próximo passo: Supabase

`supabase/previsao_schema.sql` propõe as tabelas que faltam no ER atual:
`medicoes_medidor`, `ocpp_meter_values`, `ocpp_status_notification`,
`clima_horario`, `previsoes` e `alertas_sindico`. O fluxo alvo:

1. ESP32 / SEMS / OCPP gravam medições.
2. O ETL (`preparar_dataset.py`) roda agendado.
3. Uma Edge Function busca a Open-Meteo e roda o modelo.
4. O resultado vai para `previsoes`, e as regras do Síndico gravam `alertas_sindico`.
5. O app lê pelo Realtime em vez de `ML_DADOS`.

O retreino é semanal, em Python, rodando de novo o `ChargeGrid_ML.ipynb`.
