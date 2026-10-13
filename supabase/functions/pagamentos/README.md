# Edge Function `pagamentos` (Mercado Pago)

Backend da API de pagamento do app. O app (`app/src/pagamento/gateway.js`) chama
`POST /functions/v1/pagamentos/{acao}` com a chave anon; o access token do Mercado Pago fica só aqui.

| Ação | Cartão | Pix | Créditos |
|---|---|---|---|
| `autorizar` | `POST /v1/payments` com `capture:false` (reserva válida por 5 dias) | `POST /v1/payments` `payment_method_id:"pix"` → QR Code + copia-e-cola | reserva interna (id `cred-...`) |
| `capturar` | `PUT /v1/payments/{id}` `{capture:true, transaction_amount}` (captura parcial) | `POST /v1/payments/{id}/refunds` `{amount: sobra}` | débito do valor final |
| `cancelar` | `PUT /v1/payments/{id}` `{status:"cancelled"}` | estorno total | libera a reserva |
| `webhook` | atualiza o status | idem (confirma o Pix) | — |

Cada operação é registrada em `transacoes_pagamento`
(`supabase/migrations/20261013000000_pagamentos.sql`) com `valor_total`,
`valor_anfitriao` (90%) e `taxa_plataforma` (10%).

## Modo de teste

Com credenciais de teste do Mercado Pago:

- **Cartão:** se o app não mandar `card_token`, a função gera o token com o cartão de teste
  Mastercard `5031 4332 1540 6351`, titular `APRO` (aprovado). A reserva e a captura parcial
  acontecem de verdade na conta de teste.
- **Pix:** o QR é gerado de verdade, mas Pix de teste não pode ser pago. Depois de 8 s a consulta
  devolve `approved` com `status_detail: "simulado_teste"` e, na captura, a cobrança pendente é
  cancelada no Mercado Pago.

## Deploy

```bash
npx supabase db push                                       # cria transacoes_pagamento
npx supabase secrets set MP_ACCESS_TOKEN=TEST-...          # Access Token de teste
npx supabase secrets set MP_PUBLIC_KEY=TEST-...            # Public Key de teste (cartão)
npx supabase secrets set MP_MODO_TESTE=sim                 # só se as credenciais de teste começarem com APP_USR-
npx supabase functions deploy pagamentos --no-verify-jwt   # o webhook do Mercado Pago chega sem JWT
```

No app: `PAG_ENDPOINT` em `src/app.js` aponta para `https://<projeto>.supabase.co/functions/v1/pagamentos`
e a prop `pagamentoModo` fica em `api`.

## Pendências para produção

- Tokenizar o cartão no app com o SDK JS do Mercado Pago (Card Form) e enviar `card_token`.
- Tirar a simulação de Pix (`MP_MODO_TESTE`) e usar credenciais de produção.
- Validar o header `x-signature` do webhook.
- Migrar o registro para `pagamentos`/`repasses` do schema completo.
- Split real para a conta da galeria: OAuth de marketplace do Mercado Pago (`application_fee`).
