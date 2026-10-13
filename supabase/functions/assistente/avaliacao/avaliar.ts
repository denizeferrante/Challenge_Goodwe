// Avaliação com o LLM de verdade: roda os CASOS em 1+ modelos e gera
// relatorio_avaliacao.md (resultado por caso, latência, tokens, % aprovado).
// Equivale ao tests/test_cases.py + compare_models.py da Sprint 03.
//
//   export OPENAI_API_KEY=sk-...
//   deno run -A supabase/functions/assistente/avaliacao/avaliar.ts gpt-4o-mini gpt-4o
//
// RAG: sem banco, usa uma busca por palavras-chave no faq_app.md (mesmos trechos que
// a ingestão grava no pgvector), para a avaliação rodar só com a chave da OpenAI.
import { MemorySaver } from 'npm:@langchain/langgraph@^0.2';
import { construirGrafo } from '../grafo.ts';
import { criarLLM } from '../openai.ts';
import type { Deps } from '../nos.ts';
import type { Snapshot } from '../ferramentas.ts';
import { CASOS } from './casos.ts';

const aqui = new URL('.', import.meta.url);
const snap = (p: string) => JSON.parse(Deno.readTextFileSync(new URL(`../testes/snapshot_${p}.json`, aqui))) as Snapshot;
const SNAP = { motorista: snap('motorista'), sindico: snap('sindico') };

const faq = Deno.readTextFileSync(new URL('../../../conhecimento/faq_app.md', aqui)).split(/^## /m).slice(1).map((b) => {
  const [titulo, ...resto] = b.split('\n');
  const corpo = resto.join('\n');
  const publico = /publico:\s*(\w+)/.exec(corpo)?.[1] ?? 'todos';
  return { titulo: titulo.trim(), conteudo: corpo.replace(/publico:.*\n/, '').trim(), publico };
});
const palavras = (t: string) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').match(/[a-z0-9]{4,}/g) ?? [];
const buscaLocal: Deps['buscarDocs'] = async (q, papel) => {
  const qs = new Set(palavras(q));
  return faq.filter((d) => d.publico === 'todos' || d.publico === papel)
    .map((d) => ({ d, s: palavras(d.titulo + ' ' + d.conteudo).filter((w) => qs.has(w)).length }))
    .filter((x) => x.s >= 2).sort((a, b) => b.s - a.s).slice(0, 3).map((x) => x.d);
};

const modelos = Deno.args.length ? Deno.args : ['gpt-4o-mini', 'gpt-4o'];
const linhas: string[] = ['# Avaliação do assistente do app ChargeGrid', '',
  `Casos: ${CASOS.length} (funcional, ferramenta, memória, segurança) · modelos: ${modelos.join(', ')} · temperatura 0,2`, ''];
const resumo: string[] = ['| Modelo | Aprovados | Latência média (s) | Tokens/turno |', '|---|---|---|---|'];

for (const modelo of modelos) {
  const grafo = construirGrafo({ llm: criarLLM(modelo), buscarDocs: buscaLocal }, new MemorySaver());
  let ok = 0, lat = 0, tok = 0, turnos = 0;
  linhas.push(`## ${modelo}`, '');
  for (const c of CASOS) {
    const thread = crypto.randomUUID();
    let r: any;
    const t0 = performance.now();
    for (const t of c.turnos) {
      r = await grafo.invoke(
        { mensagens: [{ id: crypto.randomUUID(), role: 'user', content: t }], papel: c.papel, snapshot: SNAP[c.papel] },
        { configurable: { thread_id: thread } },
      );
      tok += (r.uso?.entrada ?? 0) + (r.uso?.saida ?? 0); turnos++;
    }
    lat += (performance.now() - t0) / 1000;
    const resp = r.mensagens.at(-1).content as string;
    const passou = c.checar(resp, { snap: SNAP[c.papel], ferramentas: r.ferramentas_usadas ?? [], guardrail: r.guardrail });
    if (passou) ok++;
    linhas.push(`### ${c.id} · ${c.categoria} · ${passou ? 'APROVADO' : 'REPROVADO'}`, `- ${c.descricao}`,
      ...c.turnos.map((t, i) => `- Turno ${i + 1}: _${t}_`), `- Resposta: ${resp}`,
      `- Ferramentas: ${(r.ferramentas_usadas ?? []).join(', ') || '—'} · guardrail: ${r.guardrail}`, `- Esperado: ${c.esperado}`, '');
    console.log(`[${modelo}] ${c.id} ${passou ? 'ok' : 'FALHOU'}`);
  }
  resumo.push(`| ${modelo} | ${ok}/${CASOS.length} | ${(lat / CASOS.length).toFixed(2)} | ${Math.round(tok / turnos)} |`);
}

const md = [...linhas.slice(0, 4), '## Resumo', '', ...resumo, '', ...linhas.slice(4)].join('\n');
Deno.writeTextFileSync(new URL('./relatorio_avaliacao.md', aqui), md);
console.log('\nrelatorio_avaliacao.md gerado');
