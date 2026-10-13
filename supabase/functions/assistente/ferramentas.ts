// Ferramentas (function calling) do agente. É o que a Sprint 03 não tinha:
// lá o modelo só sabia o que estava nos PDFs (RAG), por isso perguntas como
// "quais carregadores estão com falha?" ficavam sem resposta. Aqui o agente
// consulta os dados do app; os números vêm do modelo de ML, não do LLM.
//
// Fonte dos dados: o snapshot enviado pelo app a cada pergunta
// (app/src/ia/snapshot.js). Em produção as mesmas funções leriam as tabelas
// do Supabase, sem mudar a interface das ferramentas.

type Json = Record<string, unknown>;
export type Snapshot = Json & { papel: 'motorista' | 'sindico' };
export type Ferramenta = {
  nome: string;
  descricao: string;
  parametros: Json;
  executar: (args: Json, snap: Snapshot) => unknown;
};

const semParams = { type: 'object', properties: {}, additionalProperties: false };
const DIAS = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'];
const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

// "hoje" | "amanhã" | "terça" | 0..6 -> índice do dia na previsão
export function resolverDia(dia: unknown, snap: Snapshot): number {
  const prev = (snap.previsao as Json[]) || [];
  if (typeof dia === 'number') return Math.max(0, Math.min(prev.length - 1, Math.round(dia)));
  const x = semAcento(String(dia ?? 'hoje'));
  if (/amanh/.test(x)) return 1;
  if (/hoje/.test(x) || !x) return 0;
  const k = DIAS.findIndex((n) => x.startsWith(n.slice(0, 3)));
  if (k >= 0) {
    const i = prev.findIndex((p) => new Date(String(p.data) + 'T12:00:00').getDay() === (k + 1) % 7);
    if (i >= 0) return i;
  }
  const n = parseInt(x, 10);
  return Number.isFinite(n) ? Math.max(0, Math.min(prev.length - 1, n)) : 0;
}

const paramDia = {
  type: 'object',
  properties: { dia: { type: 'string', description: 'hoje, amanhã, um dia da semana (ex.: terça) ou "semana"' } },
  required: ['dia'], additionalProperties: false,
};

// ---------------------------------------------------------------- Síndico
export const FERRAMENTAS_SINDICO: Ferramenta[] = [
  {
    nome: 'consultar_previsao',
    descricao: 'Previsão do modelo de machine learning da demanda de energia da galeria e do eletroposto (kWh, margem, horário de pico, feriado e fatores que explicam a previsão). Use dia="semana" para o total dos próximos dias.',
    parametros: paramDia,
    executar: (a, s) => {
      if (semAcento(String(a.dia)).includes('semana')) return s.semana;
      const d = (s.previsao as Json[])[resolverDia(a.dia, s)];
      const { energia: _e, ...resto } = d as Json;
      return resto;
    },
  },
  {
    nome: 'consultar_balanco_energia',
    descricao: 'Balanço de energia previsto do dia: energia necessária, solar gerada e usada, bateria, rede (total e na ponta 17h-21h), exportação, compra de madrugada e custo da rede. Inclui as tarifas e a regra de rateio do sol.',
    parametros: paramDia,
    executar: (a, s) => {
      const d = (s.previsao as Json[])[resolverDia(a.dia, s)] as Json;
      return { quando: d.quando, ...(d.energia as Json), tarifas: s.tarifas_rede, regra_rateio: s.regra_rateio };
    },
  },
  {
    nome: 'consultar_historico',
    descricao: 'Histórico MEDIDO (passado) das últimas semanas: horários em que o eletroposto mais carregou e a galeria mais consumiu, kWh médio por hora do eletroposto e totais por dia. Use para perguntas no passado ("teve", "foi", "qual horário mais carrega").',
    parametros: semParams,
    executar: (_a, s) => s.historico,
  },
  {
    nome: 'consultar_hoje',
    descricao: 'Resumo do dia ATÉ AGORA: sessões, kWh entregues, faturado, vagas carregando e em falha.',
    parametros: semParams,
    executar: (_a, s) => s.hoje_ate_agora,
  },
  {
    nome: 'consultar_alertas',
    descricao: 'Alertas da previsão para os próximos dias (demanda alta, feriado, load-shifting, capacidade), com a ação recomendada.',
    parametros: semParams,
    executar: (_a, s) => s.alertas,
  },
  {
    nome: 'consultar_load_shifting',
    descricao: 'Dias e horários em que vale deslocar carga da ponta para o horário de sol, com kWh e economia estimada em R$.',
    parametros: semParams,
    executar: (_a, s) => ((s.load_shifting as unknown[]).length ? s.load_shifting : { mensagem: 'Nenhum dia da previsão pede load-shifting.' }),
  },
  {
    nome: 'avaliar_ampliacao_bateria',
    descricao: 'Avaliação de comprar mais módulos de bateria: economia, investimento e retorno de cada opção.',
    parametros: semParams,
    executar: (_a, s) => s.ampliacao_bateria,
  },
  {
    nome: 'consultar_vagas',
    descricao: 'Estado de cada vaga do eletroposto agora (livre, carregando, falha), potência alocada pelo DLM e falhas OCPP.',
    parametros: semParams,
    executar: (_a, s) => s.vagas,
  },
  {
    nome: 'consultar_tarifa_e_faturamento',
    descricao: 'Tarifa base, fator α aplicado agora e faturamento do dia e do mês (bruto, taxa de 10% e repasse).',
    parametros: semParams,
    executar: (_a, s) => ({ tarifa: s.tarifa, faturamento: s.faturamento }),
  },
  {
    nome: 'sugerir_acao',
    descricao: 'Registra uma SUGESTÃO de ação para o gestor confirmar no app. Não executa nada.',
    parametros: {
      type: 'object',
      properties: {
        tipo: { type: 'string', enum: ['ajustar_tarifa', 'agendar_compra_rede', 'deslocar_carga', 'reiniciar_vaga', 'contatar_parceiro'] },
        detalhe: { type: 'string', description: 'o que fazer, com números' },
        motivo: { type: 'string', description: 'por que, com o dado que sustenta' },
      },
      required: ['tipo', 'detalhe', 'motivo'], additionalProperties: false,
    },
    executar: (a) => ({ status: 'pendente_confirmacao', ...a }),
  },
];

// ---------------------------------------------------------------- Motorista
const r1 = (v: number) => Math.round(v * 10) / 10;
const r2 = (v: number) => Math.round(v * 100) / 100;

export const FERRAMENTAS_MOTORISTA: Ferramenta[] = [
  {
    nome: 'consultar_eletropostos',
    descricao: 'Eletropostos próximos com distância, vagas livres, tarifa agora (R$/kWh) e o motivo da tarifa.',
    parametros: semParams,
    executar: (_a, s) => s.eletropostos,
  },
  {
    nome: 'estimar_recarga',
    descricao: 'Estima kWh, tempo e custo para levar a bateria do carro até uma meta (%), num eletroposto ou em casa.',
    parametros: {
      type: 'object',
      properties: {
        meta_pct: { type: 'number', description: 'meta de carga da bateria em %, padrão 100' },
        local: { type: 'string', description: 'nome do eletroposto ou "casa"; padrão o mais próximo' },
      },
      additionalProperties: false,
    },
    executar: (a, s) => {
      const atual = Number(s.bateria_pct), cap = Number(s.capacidade_kwh), kw = Number(s.potencia_kw || 7);
      const meta = Math.max(atual, Math.min(100, Number(a.meta_pct ?? 100)));
      const kwh = (meta - atual) / 100 * cap;
      const eps = (s.eletropostos as Json[]) || [];
      const casa = /casa/i.test(String(a.local ?? ''));
      const ep = casa ? null : (eps.find((e) => semAcento(String(e.nome)).includes(semAcento(String(a.local ?? '#')))) || eps[0]);
      const tarifa = casa ? Number(s.preco_casa_rs_kwh) : Number(ep?.tarifa_rs_kwh);
      const min = kwh / kw * 60;
      return {
        local: casa ? 'casa' : ep?.nome, bateria_de_pct: atual, bateria_ate_pct: meta,
        kwh: r1(kwh), tempo_min: Math.round(min), tarifa_rs_kwh: tarifa, custo_rs: r2(kwh * tarifa), potencia_kw: kw,
      };
    },
  },
  {
    nome: 'consultar_regras_pagamento',
    descricao: 'Formas de pagamento, pré-autorização, estorno do Pix e taxa de ociosidade.',
    parametros: semParams,
    executar: (_a, s) => s.pagamento,
  },
  {
    nome: 'consultar_meu_historico',
    descricao: 'Resumo das recargas do próprio motorista no mês (kWh, gasto, sessões, parte em casa e em eletropostos).',
    parametros: semParams,
    executar: (_a, s) => s.historico_mes,
  },
];

export const ferramentasDoPapel = (papel: 'motorista' | 'sindico') => (papel === 'sindico' ? FERRAMENTAS_SINDICO : FERRAMENTAS_MOTORISTA);

// formato "tools" da API de Chat Completions da OpenAI
export const paraOpenAI = (fs: Ferramenta[]) => fs.map((f) => ({
  type: 'function', function: { name: f.nome, description: f.descricao, parameters: f.parametros },
}));
