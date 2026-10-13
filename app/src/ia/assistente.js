// ---- cliente do assistente de IA --------------------------------------------
// Mesmo padrão do gateway de pagamento: dois modos com a mesma interface.
//   sandbox -> responde com as regras locais do app (sem rede, como antes)
//   api     -> POST na Edge Function supabase/functions/assistente (LangGraph +
//              OpenAI + RAG no pgvector + ferramentas sobre o snapshot do app)
// Se a API falhar, cai nas regras locais e avisa no rodapé da resposta.
const AssistenteIA = (() => {
  let cfg = { modo: 'sandbox', endpoint: '', token: '' };
  const configurar = (c) => { cfg = { ...cfg, ...(c || {}) }; return cfg; };
  const threads = {};
  const threadDe = (papel) => threads[papel] || (threads[papel] = papel + '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6));
  const novaConversa = (papel) => { delete threads[papel]; };

  // { papel, pergunta, snapshot, local: () => string }
  const perguntar = async (b) => {
    if (cfg.modo === 'api' && cfg.endpoint) {
      try {
        const r = await fetch(cfg.endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(cfg.token ? { Authorization: 'Bearer ' + cfg.token, apikey: cfg.token } : {}) },
          body: JSON.stringify({ thread_id: threadDe(b.papel), papel: b.papel, pergunta: b.pergunta, snapshot: b.snapshot }),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.erro || 'HTTP ' + r.status);
        return { ...j, origem: 'api' };
      } catch (e) {
        return { resposta: b.local(), origem: 'local', aviso: 'IA indisponível (' + e.message + '); resposta das regras locais.' };
      }
    }
    await new Promise(r => setTimeout(r, 450));
    return { resposta: b.local(), origem: 'local' };
  };

  return { configurar, perguntar, novaConversa, config: () => cfg };
})();
