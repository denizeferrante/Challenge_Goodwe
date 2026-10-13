// Edge Function do Supabase: API de pagamento do ChargeGrid (Mercado Pago).
//
// O app chama POST /functions/v1/pagamentos/{acao} com a chave anon do projeto.
// O access token do Mercado Pago fica SÓ aqui (secret MP_ACCESS_TOKEN), nunca no app.
//
//   autorizar  { recarga_id?, metodo: 'cartao'|'pix'|'creditos', valor, card_token?, payer_email? }
//   consultar  { id }
//   capturar   { id, valor_final }      -> cartão: captura parcial; Pix: estorno da sobra
//   cancelar   { id }
//   webhook    (notificação do Mercado Pago: payment.updated)
//
// Cada operação fica registrada na tabela `transacoes_pagamento`
// (supabase/migrations/20261013000000_pagamentos.sql), com o split 90/10.
//
// Modo de teste (credenciais de teste do Mercado Pago):
//   - cartão: sem card_token vindo do app, gera o token com o cartão de teste
//     Mastercard 5031 4332 1540 6351 / titular APRO (pagamento aprovado);
//   - Pix: o Mercado Pago gera o QR de verdade, mas não dá para pagar Pix de
//     teste; por isso, 8 s depois a consulta devolve "approved" com
//     status_detail "simulado_teste" para o fluxo do app seguir.
//
// Secrets:  MP_ACCESS_TOKEN (obrigatório), MP_PUBLIC_KEY (cartão de teste),
//           MP_MODO_TESTE=sim (se as credenciais de teste começarem com APP_USR-)
// Deploy:   npx supabase functions deploy pagamentos --no-verify-jwt
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.4";

const MP = "https://api.mercadopago.com";
const TOKEN = Deno.env.get("MP_ACCESS_TOKEN") ?? "";
const PUBLIC_KEY = Deno.env.get("MP_PUBLIC_KEY") ?? "";
const TESTE = TOKEN.startsWith("TEST-") || Deno.env.get("MP_MODO_TESTE") === "sim";
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

const r2 = (v: number) => Math.round(v * 100) / 100;
const split = (v: number) => ({ anfitriao: r2(v * 0.9), plataforma: r2(v - r2(v * 0.9)) });
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info, x-idempotency-key",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });

async function mp(path: string, method: string, body?: unknown, idem?: string) {
  const r = await fetch(MP + path, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
      "X-Idempotency-Key": idem ?? crypto.randomUUID(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const causa = j.cause?.[0]?.description ?? j.message ?? "Erro no Mercado Pago";
    throw Object.assign(new Error(`Mercado Pago: ${causa}`), { status: r.status >= 500 ? 502 : r.status, codigo: j.error });
  }
  return j;
}

// token de cartão de teste (só em modo de teste; em produção o app manda o card_token)
async function tokenCartaoTeste() {
  if (!PUBLIC_KEY) throw Object.assign(new Error("Defina o secret MP_PUBLIC_KEY para testar cartão."), { status: 400 });
  const r = await fetch(`${MP}/v1/card_tokens?public_key=${PUBLIC_KEY}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      card_number: "5031433215406351",
      security_code: "123",
      expiration_month: 11,
      expiration_year: 2030,
      cardholder: { name: "APRO", identification: { type: "CPF", number: "12345678909" } },
    }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.id) throw Object.assign(new Error("Mercado Pago recusou o cartão de teste: " + (j.message ?? r.status)), { status: 400 });
  return j.id as string;
}

// registro no banco: se a tabela não existir, a cobrança segue e o erro vai para o log
async function registrar(gateway_id: string, campos: Record<string, unknown>) {
  const { error } = await db.from("transacoes_pagamento").upsert({ gateway_id, ...campos, atualizado_em: new Date().toISOString() }, { onConflict: "gateway_id" });
  if (error) console.error("transacoes_pagamento:", error.message);
}

// resposta no formato que o app (src/pagamento/gateway.js) espera
const saida = (p: any, metodo: string) => ({
  id: String(p.id),
  metodo,
  status: p.status, // pending | authorized | approved | cancelled | refunded
  status_detail: p.status_detail,
  valor_autorizado: p.transaction_amount,
  cartao: p.card?.last_four_digits ? { bandeira: p.payment_method_id, final: p.card.last_four_digits } : undefined,
  pix: p.point_of_interaction?.transaction_data
    ? {
      copia_e_cola: p.point_of_interaction.transaction_data.qr_code,
      qr_base64: p.point_of_interaction.transaction_data.qr_code_base64,
      expira_em: p.date_of_expiration,
    }
    : undefined,
});

// Pix de teste não pode ser pago: depois de 8 s tratamos como aprovado
const pixTesteAprovado = (p: any) =>
  TESTE && p.payment_method_id === "pix" && p.status === "pending" &&
  Date.now() - new Date(p.date_created).getTime() > 8000;

// créditos da carteira: reserva interna, sem provedor (ids "cred-...")
const CRED = "cred-";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (!TOKEN) return json({ mensagem: "Secret MP_ACCESS_TOKEN não configurado na função." }, 500);
  const acao = new URL(req.url).pathname.split("/").pop();
  const idem = req.headers.get("x-idempotency-key") ?? undefined;
  const b = await req.json().catch(() => ({}));
  const id = b.id != null ? String(b.id) : "";

  try {
    if (acao === "autorizar") {
      const valor = r2(Number(b.valor));
      if (!(valor > 0)) return json({ mensagem: "Valor inválido." }, 400);
      const recarga = String(b.recarga_id ?? "app-" + Date.now());

      if (b.metodo === "creditos") {
        if (b.saldo != null && Number(b.saldo) < valor) {
          return json({ mensagem: "Saldo insuficiente para a pré-autorização.", codigo: "saldo_insuficiente" }, 402);
        }
        const p = { id: CRED + crypto.randomUUID(), status: "approved", status_detail: "reserved", transaction_amount: valor };
        await registrar(p.id, { recarga_ref: recarga, metodo: "creditos", status: p.status, valor_autorizado: valor });
        return json(saida(p, "creditos"));
      }

      const base = {
        transaction_amount: valor,
        description: `Recarga ChargeGrid ${recarga}`,
        external_reference: recarga,
        payer: { email: b.payer_email ?? Deno.env.get("MP_PAYER_EMAIL") ?? "test_user_chargegrid@testuser.com" },
        notification_url: `${Deno.env.get("SUPABASE_URL")}/functions/v1/pagamentos/webhook`,
      };
      let p: any;
      if (b.metodo === "pix") {
        // Pix não tem pré-autorização: cobra a estimativa e estorna a sobra na captura
        p = await mp("/v1/payments", "POST", {
          ...base,
          payment_method_id: "pix",
          date_of_expiration: new Date(Date.now() + 15 * 60_000).toISOString(),
        }, idem);
      } else {
        // cartão: reserva (capture:false) e captura só os kWh entregues no fim
        let token = b.card_token;
        let bandeira = b.payment_method_id;
        if (!token) {
          if (!TESTE) return json({ mensagem: "Falta o card_token do cartão." }, 400);
          token = await tokenCartaoTeste();
          bandeira = "master";
        }
        p = await mp("/v1/payments", "POST", { ...base, token, payment_method_id: bandeira, installments: 1, capture: false }, idem);
        if (p.status === "rejected") {
          return json({ mensagem: "Cartão recusado (" + p.status_detail + ").", codigo: p.status_detail }, 402);
        }
      }
      await registrar(String(p.id), { recarga_ref: recarga, metodo: b.metodo, status: p.status, valor_autorizado: valor });
      return json(saida(p, b.metodo));
    }

    if (acao === "consultar") {
      if (id.startsWith(CRED)) return json({ id, metodo: "creditos", status: "approved", status_detail: "reserved" });
      const p = await mp(`/v1/payments/${id}`, "GET");
      if (pixTesteAprovado(p)) return json({ ...saida(p, "pix"), status: "approved", status_detail: "simulado_teste" });
      return json(saida(p, p.payment_method_id === "pix" ? "pix" : "cartao"));
    }

    if (acao === "capturar") {
      const pedido = r2(Math.max(0, Number(b.valor_final) || 0));
      let autorizado: number, detalhe: string;

      if (id.startsWith(CRED)) {
        const { data } = await db.from("transacoes_pagamento").select("valor_autorizado").eq("gateway_id", id).maybeSingle();
        autorizado = Number(data?.valor_autorizado ?? pedido);
        detalhe = "accredited";
      } else {
        const atual = await mp(`/v1/payments/${id}`, "GET");
        autorizado = atual.transaction_amount;
        const final = r2(Math.min(pedido, autorizado));
        if (atual.payment_method_id === "pix") {
          if (atual.status === "approved") {
            const sobra = r2(autorizado - final);
            if (sobra > 0) await mp(`/v1/payments/${id}/refunds`, "POST", { amount: sobra }, idem);
            detalhe = sobra > 0 ? "partially_refunded" : "accredited";
          } else if (pixTesteAprovado(atual)) {
            // teste: o Pix nunca foi pago de verdade; cancela a cobrança pendente no Mercado Pago
            await mp(`/v1/payments/${id}`, "PUT", { status: "cancelled" }).catch(() => {});
            detalhe = "simulado_teste";
          } else {
            return json({ mensagem: "O Pix ainda não foi pago." }, 409);
          }
        } else if (final > 0) {
          // captura parcial: o restante da reserva volta para o limite do cartão
          await mp(`/v1/payments/${id}`, "PUT", { capture: true, transaction_amount: final }, idem);
          detalhe = "accredited";
        } else {
          await mp(`/v1/payments/${id}`, "PUT", { status: "cancelled" }, idem);
          detalhe = "cancelled";
        }
      }

      const final = r2(Math.min(pedido, autorizado));
      const s = split(final);
      await registrar(id, {
        status: final > 0 ? "approved" : "cancelled",
        valor_total: final,
        valor_anfitriao: s.anfitriao,
        taxa_plataforma: s.plataforma,
        processado_em: new Date().toISOString(),
      });
      return json({ id, status: final > 0 ? "approved" : "cancelled", status_detail: detalhe, valor_capturado: final, liberado: r2(autorizado - final), split: s });
    }

    if (acao === "cancelar") {
      if (id.startsWith(CRED)) {
        await registrar(id, { status: "cancelled" });
        return json({ id, status: "cancelled" });
      }
      const atual = await mp(`/v1/payments/${id}`, "GET");
      const p = atual.status === "approved"
        ? await mp(`/v1/payments/${id}/refunds`, "POST", {}, idem) // Pix já pago: estorno total
        : await mp(`/v1/payments/${id}`, "PUT", { status: "cancelled" }, idem);
      await registrar(id, { status: "cancelled" });
      return json({ id, status: p.status ?? "cancelled" });
    }

    if (acao === "webhook") {
      // Mercado Pago avisa mudanças (ex.: Pix pago). Em produção, validar o header x-signature.
      const pid = b?.data?.id;
      if (pid) {
        const p = await mp(`/v1/payments/${pid}`, "GET");
        await registrar(String(pid), { status: p.status });
      }
      return json({ ok: true });
    }

    return json({ mensagem: "Ação desconhecida." }, 404);
  } catch (e) {
    console.error(acao, (e as Error).message);
    return json({ mensagem: (e as Error).message, codigo: (e as any).codigo }, (e as any).status ?? 500);
  }
});
