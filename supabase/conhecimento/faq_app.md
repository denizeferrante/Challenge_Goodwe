# FAQ do ChargeGrid (base do RAG)

Cada seção vira um trecho na tabela `ia_conhecimento`. A linha `publico:` define quem
pode recuperar o trecho (todos, motorista ou sindico). Complete com o FAQ real do
HCA G2 usado na Sprint 2 (`CONHECIMENTO_COMPLEMENTAR` do `rag.py`) e com os PDFs em
`supabase/conhecimento/*.pdf`.

## LED e fim de carregamento do HCA G2
publico: todos
LED branco pulsante: aguardando conexão do veículo (standby). LED azul fixo ou pulsante:
carregando. LED verde fixo: carga concluída. No app, a sessão ao vivo mostra os kWh
entregues e avisa quando a meta é atingida.

## Como iniciar uma recarga no eletroposto
publico: motorista
Na vaga, toque em "Já estou no eletroposto" e leia o QR Code impresso na wallbox. Escolha
o modo (tempo, kWh ou km), a forma de pagamento e toque em "Pagar e liberar carga". A
tarifa trava no momento em que o cabo é conectado.

## Pagamento e pré-autorização
publico: motorista
Cartão: o app reserva o valor estimado e, no fim, cobra só os kWh entregues; o restante
volta ao limite. Pix: o motorista paga a estimativa e recebe de volta, na hora, o valor dos
kWh não usados. Créditos da carteira: reserva no saldo e débito do consumo.

## Taxa de ociosidade
publico: motorista
Depois de encerrar a recarga há 10 minutos de tolerância para liberar a vaga. Passado o
prazo, a vaga cobra R$ 0,90 por minuto até o cabo ser desconectado.

## Fator alfa da tarifa
publico: todos
O gestor define a tarifa base. A IA aplica o fator α conforme o cenário: excedente solar
alto reduz 12%, pouco sol aumenta 4% e o horário de ponta (17h às 21h) aumenta 18%. O
motorista vê só o preço final, travado ao plugar.

## Rateio da energia solar
publico: sindico
Com a galeria aberta, até 80% da geração solar vai para o eletroposto e o restante para a
galeria. É uma prioridade, não um teto: se sobra sol, a galeria usa a sobra, e nunca se
compra energia da rede enquanto houver excedente solar. Depois, a sobra carrega a bateria e
o que ainda sobrar é exportado (crédito de R$ 0,60/kWh).

## Bateria e horário de ponta
publico: sindico
A bateria guarda a sobra de sol e descarrega na ponta (17h às 21h), quando a energia da
rede custa R$ 1,50/kWh contra R$ 0,85/kWh fora da ponta. Load-shifting: quando a
previsão indica pouco sol ou espaço livre na bateria, vale comprar energia de madrugada,
fora da ponta, e usar no pico; ou deslocar recargas para o horário de sol.

## DLM (gestão dinâmica de carga)
publico: sindico
O medidor inteligente lê a demanda da galeria e o DLM reparte o que sobra da demanda
contratada (55 kW, com margem de 12%) igualmente entre as vagas em carga, pelo protocolo
OCPP 1.6 (SetChargingProfile). Assim o pico nunca ultrapassa o contratado.

## Previsão de demanda (machine learning)
publico: sindico
Dois modelos Random Forest, um para a galeria e outro para o eletroposto, preveem o
consumo hora a hora para os próximos 7 dias usando calendário (feriados, datas
comerciais, férias), clima (Open-Meteo) e histórico. Um classificador indica as horas de
demanda Alta e o K-Means agrupa o perfil do dia. Erro médio diário: cerca de 6% na
galeria e 37% no eletroposto, que tem poucas sessões por dia.

## Segurança elétrica e instalação
publico: todos
Instalação, manutenção ou qualquer intervenção na parte elétrica devem ser feitas por
eletricista habilitado, seguindo a NBR 5410 e as orientações do fabricante. O app ajuda
a encontrar instaladores credenciados GoodWe.
