// Chamadas à OpenAI (chat com function calling + embeddings) via REST.
// A chave fica só no secret OPENAI_API_KEY do Supabase, nunca no app.
import type { Deps, Papel } from './nos.ts';

const BASE = 'https://api.openai.com/v1';
const chave = () => {
  const k = Deno.env.get('OPENAI_API_KEY');
  if (!k) throw new Error('OPENAI_API_KEY não configurada');
  return k;
};

async function post(caminho: string, corpo: unknown) {
  const r = await fetch(BASE + caminho, {
    method: 'POST',
    headers: { Authorization: `Bearer ${chave()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error?.message ?? `OpenAI ${r.status}`);
  return j;
}

export const criarLLM = (modelo: string, temperatura = 0.2): Deps['llm'] => async (mensagens, tools) => {
  const j = await post('/chat/completions', { model: modelo, temperature: temperatura, messages: mensagens, tools, tool_choice: 'auto' });
  const m = j.choices[0].message;
  return { content: m.content, tool_calls: m.tool_calls, uso: { entrada: j.usage?.prompt_tokens ?? 0, saida: j.usage?.completion_tokens ?? 0 } };
};

export async function embedding(texto: string, modelo = 'text-embedding-3-small'): Promise<number[]> {
  const j = await post('/embeddings', { model: modelo, input: texto });
  return j.data[0].embedding;
}

// RAG: embedding da pergunta + busca no pgvector (função buscar_conhecimento da migration)
// deno-lint-ignore no-explicit-any
export const criarBuscaDocs = (supabase: any): Deps['buscarDocs'] => async (pergunta: string, papel: Papel) => {
  const consulta = await embedding(pergunta);
  const { data, error } = await supabase.rpc('buscar_conhecimento', { consulta, papel, k: 4 });
  if (error) throw new Error('RAG: ' + error.message);
  return (data ?? []).map((d: { titulo: string; conteudo: string }) => ({ titulo: d.titulo, conteudo: d.conteudo }));
};
