// Edge Function `assistente`: chatbot do motorista e Síndico Virtual do gestor.
//
// POST /functions/v1/assistente
//   { thread_id, papel: 'motorista'|'sindico', pergunta, snapshot }
// -> { resposta, guardrail, fora_de_escopo, ferramentas, fontes, acoes, modelo, latencia_ms }
//
// Secrets: OPENAI_API_KEY, OPENAI_MODEL (padrão gpt-4o-mini), SUPABASE_DB_URL (checkpointer)
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';
import { construirGrafo, criarCheckpointer } from './grafo.ts';
import { criarBuscaDocs, criarLLM } from './openai.ts';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, apikey, content-type',
};
const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
const MODELO = Deno.env.get('OPENAI_MODEL') ?? 'gpt-4o-mini';
// grafo compilado uma vez por instância da função
const grafo = construirGrafo({ llm: criarLLM(MODELO), buscarDocs: criarBuscaDocs(db) }, await criarCheckpointer());

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  if (req.method !== 'POST') return json({ erro: 'use POST' }, 405);

  // usuário logado (JWT do Supabase Auth); o papel vem do perfil, não do corpo, em produção
  const jwt = (req.headers.get('authorization') ?? '').replace(/^Bearer\s+/i, '');
  const { data: auth } = jwt ? await db.auth.getUser(jwt) : { data: { user: null } };

  const b = await req.json().catch(() => null);
  if (!b?.pergunta || !b?.thread_id) return json({ erro: 'thread_id e pergunta são obrigatórios' }, 400);
  const papel = b.papel === 'sindico' ? 'sindico' : 'motorista';
  const pergunta = String(b.pergunta).slice(0, 1000);

  const t0 = performance.now();
  try {
    const r = await grafo.invoke(
      { mensagens: [{ id: crypto.randomUUID(), role: 'user', content: pergunta }], papel, snapshot: { ...(b.snapshot ?? {}), papel } },
      { configurable: { thread_id: `${auth?.user?.id ?? 'anon'}:${b.thread_id}` } },
    );
    const resposta = r.mensagens[r.mensagens.length - 1]?.content ?? '';
    const latencia_ms = Math.round(performance.now() - t0);

    await db.from('ia_turnos').insert({
      thread_id: b.thread_id, usuario_id: auth?.user?.id ?? null, papel, pergunta, resposta,
      guardrail: r.guardrail, fora_de_escopo: r.fora_de_escopo, ferramentas: r.ferramentas_usadas, fontes: r.fontes,
      modelo: MODELO, latencia_ms, tokens_entrada: r.uso?.entrada, tokens_saida: r.uso?.saida,
    });
    if (r.acoes?.length) {
      await db.from('ia_acoes_sugeridas').insert(r.acoes.map((a: Record<string, unknown>) => ({ thread_id: b.thread_id, tipo: a.tipo, detalhe: a })));
    }
    return json({
      resposta, guardrail: r.guardrail, fora_de_escopo: r.fora_de_escopo,
      ferramentas: r.ferramentas_usadas, fontes: r.fontes, acoes: r.acoes, modelo: MODELO, latencia_ms,
    });
  } catch (e) {
    return json({ erro: (e as Error).message }, 500);
  }
});
