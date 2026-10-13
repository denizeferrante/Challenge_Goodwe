// ---- gateway de pagamento -------------------------------------------------
// Cliente da API de pagamento do ChargeGrid. O app NUNCA fala direto com o
// provedor (Mercado Pago) nem guarda o access token: ele chama a Edge Function
// supabase/functions/pagamentos, que tem o token em variável de ambiente,
// grava a tabela `pagamentos` e faz o split 90/10 (galeria / GoodWe).
//
// Dois modos, com a MESMA interface:
//   sandbox -> simula as respostas da API no navegador (protótipo, sem rede)
//   api     -> POST {endpoint}/{acao} na Edge Function
//
// Fluxo por método (mapeado para a API de Pagamentos do Mercado Pago):
//   cartao   : autorizar = POST /v1/payments com capture:false (pré-autorização,
//              vale 5 dias) -> capturar = PUT /v1/payments/{id}
//              {capture:true, transaction_amount: valor_final} (captura parcial;
//              o restante da reserva é liberado no cartão)
//   pix      : autorizar = POST /v1/payments payment_method_id:"pix" com o valor
//              estimado -> devolve QR Code + copia-e-cola; webhook confirma ->
//              capturar = POST /v1/payments/{id}/refunds {amount: sobra}
//              (Pix não tem pré-autorização: cobra a estimativa e estorna a diferença)
//   creditos : débito do saldo da carteira (tabela interna, sem provedor)
const Pagamentos = (() => {
  let cfg = { modo: 'sandbox', endpoint: '', token: '', provedor: 'Mercado Pago' };
  const configurar = (c) => { cfg = { ...cfg, ...(c || {}) }; return cfg; };
  const config = () => cfg;

  const r2 = (v) => Math.round(v * 100) / 100;
  const idempotencia = () => 'cg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  const split = (total) => ({ anfitriao: r2(total * 0.9), plataforma: r2(total - r2(total * 0.9)) });

  // ---------------------------------------------------------------- sandbox
  const SB = {};
  let seq = 1360000;
  const espera = (ms) => new Promise(r => setTimeout(r, ms));
  const pixPayload = (valor, id) => {
    // formato EMV do Pix (BR Code); chave e txid fictícios do sandbox
    const v = valor.toFixed(2);
    return '00020101021226850014br.gov.bcb.pix2563qr.sandbox.chargegrid.app/pix/v2/' + id
      + '5204000053039865406' + v.length.toString().padStart(2, '0') + v
      + '5802BR5919CHARGEGRID GOODWE6009SAO PAULO62070503***6304' + (id % 9973).toString(16).toUpperCase().padStart(4, '0');
  };
  const sandbox = {
    autorizar: async (b) => {
      await espera(b.metodo === 'pix' ? 500 : 900);
      const id = ++seq;
      if (b.metodo === 'creditos') {
        if (b.saldo != null && b.saldo < b.valor) throw Object.assign(new Error('Saldo insuficiente para a pré-autorização.'), { codigo: 'saldo_insuficiente' });
        SB[id] = { id, metodo: 'creditos', status: 'approved', status_detail: 'reserved', valor_autorizado: r2(b.valor) };
      } else if (b.metodo === 'pix') {
        SB[id] = { id, metodo: 'pix', status: 'pending', status_detail: 'pending_waiting_transfer', valor_autorizado: r2(b.valor),
          criado: Date.now(), pix: { copia_e_cola: pixPayload(b.valor, id), expira_em: new Date(Date.now() + 15 * 60000).toISOString() } };
      } else {
        SB[id] = { id, metodo: 'cartao', status: 'authorized', status_detail: 'pending_capture', valor_autorizado: r2(b.valor),
          cartao: { bandeira: 'visa', final: '4417' } };
      }
      return { ...SB[id] };
    },
    consultar: async (b) => {
      await espera(250);
      const p = SB[b.id];
      if (!p) throw new Error('Pagamento não encontrado.');
      // no sandbox o banco "paga" o Pix 4 s depois de gerado o QR
      if (p.metodo === 'pix' && p.status === 'pending' && Date.now() - p.criado > 4000) {
        p.status = 'approved'; p.status_detail = 'accredited';
      }
      return { ...p };
    },
    capturar: async (b) => {
      await espera(800);
      const p = SB[b.id];
      if (!p) throw new Error('Pagamento não encontrado.');
      const final = r2(Math.min(b.valor_final, p.valor_autorizado));
      p.valor_capturado = final;
      p.liberado = r2(p.valor_autorizado - final);
      p.status = 'approved';
      p.status_detail = p.metodo === 'pix' ? (p.liberado > 0 ? 'partially_refunded' : 'accredited') : 'accredited';
      p.split = split(final);
      return { ...p };
    },
    cancelar: async (b) => {
      await espera(500);
      const p = SB[b.id];
      if (!p) return { id: b.id, status: 'cancelled' };
      p.status = p.metodo === 'pix' && p.status === 'approved' ? 'refunded' : 'cancelled';
      p.liberado = p.valor_autorizado; p.valor_capturado = 0;
      return { ...p };
    },
  };

  // ---------------------------------------------------------------- api
  const api = async (acao, b) => {
    const r = await fetch(cfg.endpoint.replace(/\/$/, '') + '/' + acao, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Idempotency-Key': b.idempotencia || idempotencia(),
        // chave anon do Supabase (pública); o token do Mercado Pago fica só na Edge Function
        ...(cfg.token ? { Authorization: 'Bearer ' + cfg.token, apikey: cfg.token } : {}),
      },
      body: JSON.stringify(b),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw Object.assign(new Error(j.mensagem || 'Falha no pagamento (' + r.status + ').'), { codigo: j.codigo });
    return j;
  };

  const chamar = (acao, b) => {
    const corpo = { ...b, idempotencia: b.idempotencia || idempotencia() };
    return cfg.modo === 'api' && cfg.endpoint ? api(acao, corpo) : sandbox[acao](corpo);
  };

  return {
    configurar, config, split,
    // { metodo: 'pix'|'cartao'|'creditos', valor, recarga_id?, saldo? }
    autorizar: (b) => chamar('autorizar', b),
    consultar: (id) => chamar('consultar', { id }),
    // { id, valor_final }
    capturar: (b) => chamar('capturar', b),
    cancelar: (id) => chamar('cancelar', { id }),
  };
})();
