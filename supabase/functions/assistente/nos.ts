// Nós do grafo do agente (mesma ideia do src/graph.py da Sprint 03), escritos
// como funções puras com dependências injetadas: o LLM, a busca no RAG e as
// ferramentas. Assim cada nó é testável sem rede (testes/nos.test.ts) e o
// grafo.ts só liga os nós no StateGraph do LangGraph.
//
// START -> guardrail_entrada -> [bloqueado?] -> recusar -> END
//                             -> recuperar -> agente <-> ferramentas
//                                          -> guardrail_saida -> END
import * as G from './guardrails.ts';
import { promptDoPapel } from './prompts.ts';
import { ferramentasDoPapel, paraOpenAI, type Snapshot } from './ferramentas.ts';

export type Papel = 'motorista' | 'sindico';
export type Msg = {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: { id: string; type: 'function'; function: { name: string; arguments: string } }[];
  tool_call_id?: string;
};
export type Estado = {
  mensagens: Msg[];
  papel: Papel;
  snapshot: Snapshot;
  contexto: string;
  fontes: string[];
  guardrail: 'ok' | 'injection' | 'lgpd' | 'saida_juridico' | 'saida_financeiro';
  fora_de_escopo: boolean;
  passos: number;
  ferramentas_usadas: string[];
  acoes: unknown[];
  uso: { entrada: number; saida: number };
};

export type RespostaLLM = { content: string | null; tool_calls?: Msg['tool_calls']; uso?: { entrada: number; saida: number } };
export type Deps = {
  llm: (mensagens: unknown[], tools: unknown[]) => Promise<RespostaLLM>;
  buscarDocs: (pergunta: string, papel: Papel) => Promise<{ titulo: string; conteudo: string }[]>;
  novoId?: () => string;
};

export const MAX_PASSOS_FERRAMENTA = 4;  // evita loop infinito agente <-> ferramentas
export const JANELA_HISTORICO = 24;      // mensagens enviadas ao LLM por turno (memória completa fica no checkpointer)

// reducer das mensagens: anexa, mas SUBSTITUI quando o id já existe
// (o guardrail de saída troca a resposta problemática sem deixá-la na memória,
// como o add_messages com id da Sprint 03)
export function juntarMensagens(atual: Msg[], novas: Msg[]): Msg[] {
  const out = [...(atual || [])];
  for (const m of novas || []) {
    const i = out.findIndex((x) => x.id === m.id);
    if (i >= 0) out[i] = m; else out.push(m);
  }
  return out;
}

const ultimaDoUsuario = (s: Estado) => [...s.mensagens].reverse().find((m) => m.role === 'user')?.content ?? '';

// recorta a janela sem separar uma resposta com tool_calls das mensagens "tool" dela
export function janela(ms: Msg[], n = JANELA_HISTORICO): Msg[] {
  if (ms.length <= n) return ms;
  let ini = ms.length - n;
  while (ini < ms.length && ms[ini].role !== 'user') ini++;
  return ms.slice(ini);
}

export function criarNos(deps: Deps) {
  let seq = 0;
  // ids únicos: o reducer substitui mensagens de mesmo id
  const novoId = deps.novoId ?? (() => globalThis.crypto?.randomUUID?.() ?? 'm' + Date.now().toString(36) + Math.random().toString(36).slice(2) + (seq++).toString(36));

  return {
    guardrail_entrada: (s: Estado): Partial<Estado> => {
      const t = ultimaDoUsuario(s);
      // zera o que é do turno (o checkpointer guarda o estado do turno anterior)
      const turno = { fora_de_escopo: G.possivelmenteForaDeEscopo(t), passos: 0, ferramentas_usadas: [], acoes: [], fontes: [], contexto: '', uso: { entrada: 0, saida: 0 } };
      if (G.detectarPromptInjection(t)) return { ...turno, guardrail: 'injection' };
      if (G.detectarPedidoDadosDeTerceiros(t)) return { ...turno, guardrail: 'lgpd' };
      return { ...turno, guardrail: 'ok' };
    },

    rota_entrada: (s: Estado): 'recusar' | 'recuperar' => (s.guardrail === 'ok' ? 'recuperar' : 'recusar'),

    recusar: (s: Estado): Partial<Estado> => ({
      mensagens: [{ id: novoId(), role: 'assistant', content: s.guardrail === 'lgpd' ? G.MSG.lgpd : G.MSG.injection }],
    }),

    recuperar: async (s: Estado): Promise<Partial<Estado>> => {
      const vistos = new Set<string>();
      // trechos repetidos (ex.: base carregada duas vezes) entram uma vez só
      const docs = (await deps.buscarDocs(ultimaDoUsuario(s), s.papel)).filter((d) => !vistos.has(d.conteudo) && vistos.add(d.conteudo));
      return {
        contexto: docs.map((d) => `[${d.titulo}]\n${d.conteudo}`).join('\n\n'),
        fontes: docs.map((d) => d.titulo),
      };
    },

    agente: async (s: Estado): Promise<Partial<Estado>> => {
      const sistema: unknown[] = [{ role: 'system', content: promptDoPapel(s.papel) }];
      if (s.contexto) sistema.push({ role: 'system', content: 'Contexto recuperado dos documentos:\n' + s.contexto });
      if (s.fora_de_escopo) sistema.push({ role: 'system', content: 'Aviso do guardrail: a pergunta parece fora do escopo GoodWe/ChargeGrid. Se for, recuse com educação e ofereça ajuda no escopo.' });
      const hist = janela(s.mensagens).map(({ id: _id, ...m }) => m);
      const r = await deps.llm([...sistema, ...hist], paraOpenAI(ferramentasDoPapel(s.papel)));
      const uso = { entrada: (s.uso?.entrada || 0) + (r.uso?.entrada || 0), saida: (s.uso?.saida || 0) + (r.uso?.saida || 0) };
      const msg: Msg = { id: novoId(), role: 'assistant', content: r.content ?? '' };
      if (r.tool_calls?.length) msg.tool_calls = r.tool_calls;
      return { mensagens: [msg], passos: (s.passos || 0) + 1, uso };
    },

    rota_agente: (s: Estado): 'ferramentas' | 'guardrail_saida' => {
      const u = s.mensagens[s.mensagens.length - 1];
      return u?.tool_calls?.length && (s.passos || 0) < MAX_PASSOS_FERRAMENTA ? 'ferramentas' : 'guardrail_saida';
    },

    ferramentas: (s: Estado): Partial<Estado> => {
      const u = s.mensagens[s.mensagens.length - 1];
      const fs = ferramentasDoPapel(s.papel);
      const usadas: string[] = [];
      const acoes: unknown[] = [];
      const respostas: Msg[] = (u.tool_calls || []).map((c) => {
        const f = fs.find((x) => x.nome === c.function.name);
        let saida: unknown;
        try {
          if (!f) throw new Error('ferramenta desconhecida: ' + c.function.name);
          saida = f.executar(JSON.parse(c.function.arguments || '{}'), s.snapshot);
          usadas.push(f.nome);
          if (f.nome === 'sugerir_acao') acoes.push(saida);
        } catch (e) {
          saida = { erro: (e as Error).message };
        }
        return { id: novoId(), role: 'tool', tool_call_id: c.id, content: JSON.stringify(saida) };
      });
      return {
        mensagens: respostas,
        ferramentas_usadas: [...(s.ferramentas_usadas || []), ...usadas],
        acoes: [...(s.acoes || []), ...acoes],
      };
    },

    guardrail_saida: (s: Estado): Partial<Estado> => {
      const u = s.mensagens[s.mensagens.length - 1];
      if (!u || u.role !== 'assistant') return {};
      // passou do limite de passos ainda pedindo ferramenta: responde com segurança
      if (u.tool_calls?.length) {
        const { tool_calls: _t, ...semFerr } = u;
        return { mensagens: [{ ...semFerr, content: u.content || 'Não consegui fechar essa resposta com os dados disponíveis. Pode reformular a pergunta?' }] };
      }
      const tipo = G.conselhoSensivel(u.content);
      if (tipo) return { guardrail: tipo === 'juridico' ? 'saida_juridico' : 'saida_financeiro', mensagens: [{ ...u, content: G.MSG[tipo] }] };
      const limpo = G.mascararDadosPessoais(u.content);
      return limpo !== u.content ? { mensagens: [{ ...u, content: limpo }] } : {};
    },
  };
}
