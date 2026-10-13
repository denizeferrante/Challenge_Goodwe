// Guardrails determinísticos do assistente (porte de src/guardrails.py da Sprint 03,
// ampliado para o app). Rodam como nós do grafo, antes e depois do LLM, e não
// dependem do modelo "lembrar" do system prompt.

// --- prompt injection (mesmos padrões da Sprint 03) ------------------------
const PADROES_INJECTION = [
  /ignore\s+(todas\s+)?(as\s+)?(suas\s+)?instru[cç][oõ]es/i,
  /esque[çc]a\s+(todas\s+)?(as\s+)?(suas\s+)?instru[cç][oõ]es/i,
  /disregard\s+(all\s+)?(previous|prior)\s+instructions/i,
  /ignore\s+(all\s+)?(previous|prior)\s+instructions/i,
  /revele?\s+(o\s+)?(seu\s+)?system\s*prompt/i,
  /mostre?\s+(o\s+)?(seu\s+)?system\s*prompt/i,
  /(qual|quais)\s+(s[ãa]o?\s+)?(suas?\s+)?instru[çc][ãa]o(es)?\s+(interna|original)/i,
  /voc[êe]\s+n[ãa]o\s+(trabalha|é)\s+mais\s+(para|da)/i,
  /a\s+partir\s+de\s+agora\s+voc[êe]\s+[ée]/i,
  /finja\s+que\s+voc[êe]\s+([ée]|n[ãa]o)/i,
  /modo\s+desenvolvedor/i,
  /\bdan\b.{0,15}(mode|modo)/i,
  /act\s+as\s+if\s+you\s+(are|have)\s+no\s+restrictions/i,
];
export const detectarPromptInjection = (t: string): boolean => PADROES_INJECTION.some((r) => r.test(t));

// --- LGPD: pedido de dados pessoais de outra pessoa (novo no app) ----------
const PADROES_LGPD = [
  /(placa|cpf|e-?mail|telefone|endere[çc]o|nome)\s+(d[oa]s?\s+)?(outr[oa]s?|algum|demais)\s+(motorista|usu[áa]rio|cliente|morador)/i,
  /quem\s+(est[áa]|estava)\s+(carregando|na\s+vaga)/i,
  /(dados|hist[óo]rico)\s+(de|d[oa])\s+(outr[oa]|outros)\s+(motorista|usu[áa]rio|cliente)/i,
];
export const detectarPedidoDadosDeTerceiros = (t: string): boolean => PADROES_LGPD.some((r) => r.test(t));

// --- escopo: sinal auxiliar não bloqueante (como na Sprint 03) -------------
const PALAVRAS_ESCOPO = [
  'goodwe', 'hca', 'carregador', 'carga', 'carregamento', 'recarga', 'recarregar', 'eletroposto', 'veículo elétrico',
  'veiculo eletrico', 'ev', 'ocpp', 'condomínio', 'condominio', 'galeria', 'wallbox', 'tomada', 'bateria', 'mobilidade',
  'vaga', 'tarifa', 'kwh', 'solar', 'energia', 'rede', 'ponta', 'previsão', 'previsao', 'amanhã', 'amanha', 'semana',
  'fatur', 'repasse', 'pagamento', 'pix', 'preço', 'preco', 'custa', 'dlm', 'demanda', 'síndico', 'sindico', 'load',
  'alerta', 'consumo', 'geração', 'geracao', 'ociosidade', 'rota', 'carro', 'pico', 'horário', 'horario',
];
export const possivelmenteForaDeEscopo = (t: string): boolean => {
  const x = ` ${t.toLowerCase()} `;
  return !PALAVRAS_ESCOPO.some((p) => x.includes(p.length <= 3 ? ` ${p} ` : p));
};

// --- saída: conselho jurídico/financeiro "profissional" -------------------
const JURIDICO = /(na\s+minha\s+opini[ãa]o\s+jur[íi]dica|legalmente\s+voc[êe]\s+deve|como\s+seu\s+advogado|isso\s+configura\s+crime)/i;
const FINANCEIRO = /(voc[êe]\s+deve\s+investir|garanto\s+(o\s+)?retorno|retorno\s+garantido|como\s+seu\s+consultor\s+financeiro)/i;
export const conselhoSensivel = (t: string): 'juridico' | 'financeiro' | null =>
  JURIDICO.test(t) ? 'juridico' : FINANCEIRO.test(t) ? 'financeiro' : null;

// --- saída: mascarar dado pessoal que escape na resposta -------------------
export const mascararDadosPessoais = (t: string): string => t
  .replace(/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g, '***.***.***-**')                         // CPF
  .replace(/\b([\w.-])[\w.-]*@([\w-]+\.)+[\w-]{2,}\b/g, (_m, a) => a + '***@***')        // e-mail
  .replace(/\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b/g, '***-****');                                // placa

export const MSG = {
  injection:
    'Não posso ignorar minhas instruções nem revelar como funciono por dentro. Posso ajudar com recarga, '
    + 'eletropostos, energia solar e o seu ChargeGrid. Como posso ajudar nesse tema?',
  lgpd:
    'Não compartilho dados de outros motoristas ou usuários: isso é protegido pela LGPD (Lei 13.709/2018). '
    + 'Posso mostrar a ocupação das vagas ou os seus próprios dados, se quiser.',
  juridico:
    'Não posso orientar juridicamente como um advogado. Recomendo consultar um profissional do direito. '
    + 'Posso ajudar com o funcionamento do eletroposto e do carregador GoodWe.',
  financeiro:
    'Não posso dar uma recomendação de investimento como um consultor financeiro. Posso mostrar os números '
    + 'da previsão e da simulação (economia, investimento e retorno estimados) para você avaliar com um especialista.',
};
