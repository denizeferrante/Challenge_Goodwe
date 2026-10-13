// Liga os nós de nos.ts num StateGraph do LangGraph.js (mesmo framework da Sprint 03).
// Memória: checkpointer Postgres do LangGraph no banco do Supabase, chaveado por
// thread_id. Resolve o trade-off do relatório da Sprint 03 (MemorySaver perdia a
// sessão ao reiniciar o processo). Sem SUPABASE_DB_URL cai no MemorySaver.
import { Annotation, END, MemorySaver, START, StateGraph } from 'npm:@langchain/langgraph@^0.2';
import { criarNos, juntarMensagens, type Deps, type Msg, type Papel } from './nos.ts';
import type { Snapshot } from './ferramentas.ts';

const ultimo = <T>(padrao: T) => Annotation<T>({ reducer: (_a: T, b: T) => b, default: () => padrao });

export const EstadoGrafo = Annotation.Root({
  mensagens: Annotation<Msg[]>({ reducer: juntarMensagens, default: () => [] }),
  papel: ultimo<Papel>('motorista'),
  snapshot: ultimo<Snapshot>({ papel: 'motorista' } as Snapshot),
  contexto: ultimo<string>(''),
  fontes: ultimo<string[]>([]),
  guardrail: ultimo<string>('ok'),
  fora_de_escopo: ultimo<boolean>(false),
  passos: ultimo<number>(0),
  ferramentas_usadas: ultimo<string[]>([]),
  acoes: ultimo<unknown[]>([]),
  uso: ultimo<{ entrada: number; saida: number }>({ entrada: 0, saida: 0 }),
});

export async function criarCheckpointer() {
  const url = Deno.env.get('SUPABASE_DB_URL');
  if (!url) return new MemorySaver();
  const { PostgresSaver } = await import('npm:@langchain/langgraph-checkpoint-postgres@^0.0');
  const saver = PostgresSaver.fromConnString(url);
  await saver.setup();
  return saver;
}

// deno-lint-ignore no-explicit-any
export function construirGrafo(deps: Deps, checkpointer: any) {
  const n = criarNos(deps);
  // deno-lint-ignore no-explicit-any
  const g = new StateGraph(EstadoGrafo) as any;
  g.addNode('guardrail_entrada', n.guardrail_entrada)
    .addNode('recusar', n.recusar)
    .addNode('recuperar', n.recuperar)
    .addNode('agente', n.agente)
    .addNode('ferramentas', n.ferramentas)
    .addNode('guardrail_saida', n.guardrail_saida)
    .addEdge(START, 'guardrail_entrada')
    .addConditionalEdges('guardrail_entrada', n.rota_entrada, { recusar: 'recusar', recuperar: 'recuperar' })
    .addEdge('recusar', END)
    .addEdge('recuperar', 'agente')
    .addConditionalEdges('agente', n.rota_agente, { ferramentas: 'ferramentas', guardrail_saida: 'guardrail_saida' })
    .addEdge('ferramentas', 'agente')
    .addEdge('guardrail_saida', END);
  return g.compile({ checkpointer });
}
