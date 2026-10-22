// Apresentação da Sprint 4 com a identidade do app (design-system/tokens.json)
const pptxgen = require('pptxgenjs');
const { execFileSync } = require('child_process');
// títulos viram imagem em Nunito: sem a fonte instalada (ex.: celular), o PowerPoint trocaria por outra
const titleImg = (text, color, pt) => { const [path, w, h] = execFileSync('python3', ['title_png.py', text, color, String(pt)]).toString().trim().split(' '); return { path, w: +w, h: +h }; };
const fs = require('fs');
const React = require('react'); const RDS = require('react-dom/server'); const sharp = require('sharp');
const Lu = require('react-icons/lu');
const { applyTheme } = require('/mnt/skills/public/pptx/scripts/apply_theme.js');
// tokens do design system
const T = { page: 'FFFFFF', card: 'FFFFFF', sunken: 'F2F3F6', border: 'E4E5E9', borderStrong: 'C9CED8',
  ink: '131C2E', muted: '7C8494', mutedStrong: '5D6572', brand: 'F5333F', brandStrong: 'C21A2C', brandSoft: 'FDEAEC',
  solar: 'F2B01E', solarSoft: 'FAEED3', solarInk: '7A5406', battery: '149D68', batterySoft: 'DCF3EA', batteryInk: '0B6B47',
  info: '3577F1', infoSoft: 'DEE9FC', infoInk: '2B57A8', lime: '9CFE33', inverse: '0E1118' };
// pesos fortes via bold:true na família Nunito: sem a fonte instalada, o fallback continua em negrito
const F = 'Nunito', FB = 'Nunito', FX = 'Nunito';
const THEME = { name: 'ChargeGrid', headFontFace: FB, bodyFontFace: F,
  colors: { dk1: T.ink, lt1: 'FFFFFF', dk2: T.mutedStrong, lt2: T.sunken, accent1: T.brand, accent2: T.battery, accent3: T.info, accent4: T.solar, accent5: T.lime, accent6: T.brandStrong, hlink: T.infoInk, folHlink: T.infoInk } };
const icon = async (Comp, color) => {
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: '#' + color, size: 256, strokeWidth: 2 }));
  return 'image/png;base64,' + (await sharp(Buffer.from(svg)).png().toBuffer()).toString('base64');
};
const dims = (f) => { const b = fs.readFileSync(f); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };
const px = (p) => p / 96; // 1 px do app = 1/96"

(async () => {
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; pres.title = 'ChargeGrid Intelligence'; pres.author = 'Equipe Ecovolts';
pres.theme = { headFontFace: FB, bodyFontFace: F };

// ---------- layouts
pres.defineSlideMaster({ title: 'Tela', background: { color: T.page },
  objects: [
    { placeholder: { options: { name: 'kicker', type: 'body', x: 0.45, y: 0.34, w: 5, h: 0.22, fontFace: FX, bold: true, fontSize: 10, color: T.brandStrong, charSpacing: 1.5, margin: 0, align: 'left', valign: 'middle' }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: 0.45, y: 0.56, w: 9.1, h: 0.5, fontFace: FB, bold: true, fontSize: 24, color: T.ink, margin: 0, align: 'left', valign: 'middle' }, text: '' } },
    { rect: { x: 9.03, y: 5.24, w: 0.52, h: 0.26, fill: { color: T.sunken }, rectRadius: 0.13 } },
  ],
  slideNumber: { x: 9.03, y: 5.24, w: 0.52, h: 0.26, fontFace: FX, bold: true, fontSize: 9, color: T.mutedStrong, align: 'center', valign: 'middle' } });
pres.defineSlideMaster({ title: 'Capa', background: { color: T.page },
  objects: [{ placeholder: { options: { name: 'kicker', type: 'body', x: 0.5, y: 0.55, w: 5.2, h: 0.26, fontFace: FX, bold: true, fontSize: 10, color: T.brandStrong, charSpacing: 1.5, margin: 0, align: 'left' }, text: '' } }] });

// seletor segmentado do app como navegação entre seções
const SEC = [[Lu.LuNetwork, 'Arquitetura'], [Lu.LuWorkflow, 'Dados'], [Lu.LuUsers, 'Personas'], [Lu.LuAward, 'Diferenciais']];
const ICONS = {}; for (const [ic, t] of SEC) { ICONS[t + 'on'] = await icon(ic, T.brand); ICONS[t + 'off'] = await icon(ic, T.muted); }
const segmented = (s, active) => {
  const widths = SEC.map(([, t]) => 0.42 + t.length * 0.072); const gap = 0.04, pad = 0.05;
  const W = widths.reduce((a, b) => a + b, 0) + gap * (SEC.length - 1) + pad * 2, H = 0.34, x0 = Math.max((10 - W) / 2, 3.15), y0 = 5.2;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0, y: y0, w: W, h: H, fill: { color: T.sunken }, line: { color: T.sunken }, rectRadius: H / 2, objectName: 'Seletor' });
  let x = x0 + pad;
  SEC.forEach(([, t], i) => {
    const w = widths[i], on = t === active, sy = y0 + pad, sh = H - pad * 2;
    if (on) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: sy, w, h: sh, fill: { color: T.card }, line: { color: T.borderStrong, width: 0.75 }, rectRadius: sh / 2, objectName: t + ' ativo' });
    s.addImage({ data: ICONS[t + (on ? 'on' : 'off')], x: x + 0.12, y: sy + (sh - 0.16) / 2, w: 0.16, h: 0.16, objectName: t + ' ícone' });
    s.addText(t, { x: x + 0.32, y: sy, w: w - 0.36, h: sh, fontFace: on ? FX : F, bold: false, fontSize: 9.5, color: on ? T.ink : T.mutedStrong, margin: 0, valign: 'middle', isTextBox: true, objectName: t });
    x += w + gap;
  });
};
const NAVY = '17243A';  // azul-marinho dos cards escuros do app (#131c2e → #1d2942)
const header = (s, n, sec, title, nav, dark = false) => {
  s.addText(dark ? [{ text: n + '  ·  ' + sec, options: { color: T.lime } }] : n + '  ·  ' + sec, { placeholder: 'kicker' });
  { const t = titleImg(title, dark ? 'FFFFFF' : T.ink, 24); s.addImage({ path: t.path, x: 0.45, y: 0.56 + (0.5 - t.h) / 2, w: t.w, h: t.h, objectName: 'Título', altText: title }); }
  segmented(s, nav);
  s.addText([{ text: 'ChargeGrid', options: { fontFace: FB, bold: true, color: T.brand } }, { text: '  Intelligence', options: { fontFace: F, color: dark ? 'AEB4C0' : T.mutedStrong } }, { text: '  |  ', options: { fontFace: F, color: dark ? '5D6572' : T.borderStrong } }, { text: 'Ecovolts', options: { fontFace: FB, bold: true, color: dark ? T.lime : '4E9A06' } }],
    { x: 0.45, y: 5.26, w: 2.8, h: 0.22, fontSize: 9.5, margin: 0, valign: 'middle', isTextBox: true, objectName: 'Marca' });
};
const figSlide = (n, sec, title, nav, img, notes, dark = false, fitH = null) => {
  const s = pres.addSlide({ masterName: 'Tela' }); if (dark) s.background = { color: NAVY }; header(s, n, sec, title, nav, dark);
  const [pw, ph] = dims(img); const r = pw / ph;
  const top = 1.22, maxH = fitH || 5.08 - top, maxW = 9.3;
  let w = maxW, h = w / r; if (h > maxH) { h = maxH; w = h * r; }
  // com altura própria, o conjunto fica centrado entre o título (1,1") e o seletor (5,15")
  const y = fitH ? 1.1 + (4.05 - h) / 2 - 0.15 : top;  // um pouco acima do centro: o seletor do rodapé pesa embaixo
  s.addImage({ path: img, x: (10 - w) / 2, y, w, h, objectName: title, altText: title });
  s.addNotes(notes); return s;
};

// ---------- capa
let s = pres.addSlide({ masterName: 'Capa' });
s.background = { path: 's_capa.png' };
s.addText('EV CHALLENGE GOODWE + FIAP 2026', { placeholder: 'kicker' });
{ const [a, b] = dims('wordmark.png'); const w = 4.5; s.addImage({ path: 'wordmark.png', x: 0.5, y: 0.9, w, h: w * b / a, objectName: 'ChargeGrid Intelligence', altText: 'ChargeGrid Intelligence' }); }
// botão de entrada do app
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 2.98, w: 3.1, h: 0.66, fill: { color: '1A2130' }, line: { color: T.lime, width: 1.25 }, rectRadius: px(18), objectName: 'Ecovolts botão' });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.62, y: 3.09, w: 0.44, h: 0.44, fill: { color: T.brand }, line: { color: T.brand }, rectRadius: px(12), objectName: 'Ecovolts ícone fundo' });
s.addImage({ data: await icon(Lu.LuZap, 'FFFFFF'), x: 0.72, y: 3.19, w: 0.24, h: 0.24, objectName: 'Ecovolts ícone' });
s.addText([{ text: 'Ecovolts', options: { fontFace: FB, bold: true, fontSize: 16, color: 'FFFFFF', breakLine: true } }, { text: 'Equipe 4 · Turma CCPW', options: { fontFace: F, fontSize: 9, color: 'AEB4C0' } }],
  { x: 1.18, y: 3.02, w: 2.1, h: 0.58, margin: 0, valign: 'middle', isTextBox: true, objectName: 'Ecovolts' });
s.addText('›', { x: 3.3, y: 2.98, w: 0.22, h: 0.66, fontFace: FB, bold: true, fontSize: 18, color: T.lime, align: 'center', valign: 'middle', margin: 0, isTextBox: true, objectName: 'Ecovolts seta' });
// pílulas das personas
[['Motorista', '0F7A51', 1.05], ['Gestor', '1D4EA8', 0.82], ['Gestor prospect', 'B56B00', 1.38]].reduce((x, [t, c, w]) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.92, w, h: 0.3, fill: { color: c }, line: { color: c }, rectRadius: 0.15, objectName: t + ' pílula' });
  s.addText(t, { x, y: 4.92, w, h: 0.3, fontFace: FX, bold: true, fontSize: 10, color: 'FFFFFF', align: 'center', valign: 'middle', margin: 0, isTextBox: true, objectName: t });
  return x + w + 0.1; }, 5.78);
// protótipo físico do carregador, sem fundo, entre o texto e os celulares
{ const [a, b] = dims('carregador.png'); const h = 2.75, w = h * a / b; s.addImage({ path: 'carregador.png', x: 4.8 - w / 2, y: 2.62, w, h, objectName: 'Protótipo do carregador', altText: 'Protótipo físico do carregador GoodWe com ESP32' }); }
s.addText('INTEGRANTES', { x: 0.5, y: 3.88, w: 4, h: 0.22, fontFace: FX, bold: true, fontSize: 10, color: T.brandStrong, charSpacing: 1.5, margin: 0, isTextBox: true, objectName: 'Integrantes título' });
const team = [['572899', 'Patrick Fernandes Martins Pais', 'Scrum Master'], ['571836', 'Bruna Yukimy Hada', 'Desenvolvedora'], ['571562', 'Denize Ferrante', 'Desenvolvedora e Product Owner'],
  ['570436', 'Gabriel Del Pizzo Pintor', 'Desenvolvedor'], ['572395', 'Gabriel Dias Menezes', 'Desenvolvedor'], ['570540', 'Ian Rodrigues Martins', 'Desenvolvedor']];
s.addText(team.flatMap(([rm, n, p], i) => [
  { text: rm + '   ', options: { fontFace: F, color: T.muted, fontSize: 9 } },
  { text: n, options: { fontFace: FX, bold: true, color: T.ink, fontSize: 9 } },
  { text: '  ·  ' + p, options: { fontFace: F, color: T.mutedStrong, fontSize: 9, breakLine: i < team.length - 1 } }]),
  { x: 0.5, y: 4.12, w: 4.6, h: 1.05, margin: 0, valign: 'top', isTextBox: true, objectName: 'Integrantes' });
s.addNotes('ChargeGrid transforma o carregador residencial GoodWe HCA G2 em eletroposto compartilhado para galerias comerciais. Vamos mostrar a arquitetura, o fluxo de dados, as três personas e os diferenciais.');

figSlide('01', 'ARQUITETURA DA SOLUÇÃO', 'Hardware e caminho dos dados', 'Arquitetura', 'w_arquitetura.png',
  'À esquerda, a camada de hardware: painéis, carport solar e fachada BIPV geram para o inversor; o CT fica depois de todas as cargas e antes do medidor da concessionária, que fatura. Em verde-limão, a nossa solução; em vermelho, o que existe na solução real mas está fora do protótipo. À direita, o fluxo de dados em quatro etapas: Inversor e Medidor (o inversor GoodWe converte corrente contínua em alternada e orquestra a energia; o medidor inteligente mede todo o fluxo), Supabase como backend, Preditividade e Síndico Virtual (geramos uma base sintética horária de 649 dias, calibrada para São Paulo e com falhas de telemetria, para treinar Random Forest e K-Means), e App, com o limite de potência do DLM voltando ao carregador. A API SEMS Plus aparece em vermelho porque é integração futura.');
figSlide('02', 'FLUXO DE DADOS', 'APIs, Supabase, ESP32 e stack', 'Dados', 'w_detalhado.png',
  'Cada linha é um fluxo, do dispositivo ao app, com linguagem e framework em azul. Seta cheia funciona hoje; tracejada é arquitetura alvo. À direita, a foto do protótipo físico do carregador, montado com o ESP32: o botão é o plugue e o LED mostra o status da vaga. Hoje funcionam a demonstração física, o mapa, a previsão, o assistente e o pagamento; recarga por OCPP e energia pela API SEMS são arquitetura alvo.');
figSlide('03', 'PERSONAS', 'Três personas, um app', 'Personas', 'w_personas.png',
  'A escolha de papel separa motorista e gestor. No gestor, ter a solução instalada leva ao painel completo; sem ela, ao modo de avaliação do prospect.', true, 3.55);
figSlide('03', 'PERSONAS  ·  MOTORISTA', 'Encontrar, carregar e pagar', 'Personas', 'w_motorista.png',
  'O motorista encontra o eletroposto, libera a carga por QR Code, acompanha a sessão e recebe o recibo com a captura só dos kWh entregues.', true);
figSlide('03', 'PERSONAS  ·  GESTOR DA GALERIA', 'Operar energia, vagas e receita', 'Personas', 'w_gestor.png',
  'O gestor acompanha energia, vagas e faturamento, ajusta a tarifa base com o fator α e conversa com o Síndico Virtual.', true);
figSlide('03', 'PERSONAS  ·  GESTOR PROSPECT', 'Avaliar antes de instalar', 'Personas', 'w_prospect.png',
  'O prospect simula a viabilidade, vê quantas vagas cabem no sol e chega aos parceiros GoodWe.', true);

// ---------- diferenciais: trechos do app em retângulos com borda verde-limão, em dois slides
const DESC = {
  ia: ['IA como motor lógico + Machine Learning', 'Random Forest prevê o consumo hora a hora; K-Means classifica o dia (R² 0,961).'],
  llm: ['LLM + RAG', 'O Síndico Virtual responde com os números do modelo e protege dados (LGPD).'],
  tarifa: ['Tarifa dinâmica com tarifa base', 'Base do gestor × fator α: tarifa binômica, ponta e 3 modos de carregamento.'],
  ls: ['Load shifting', 'Compra energia fora de ponta e usa na ponta só quando a previsão mostra economia.'],
  eco: ['Ecossistema GoodWe', 'O simulador soma cobertura solar, fachada BIPV, carport e baterias GoodWe ao que a galeria já tem.'],
  dash: ['Dashboards de energia e financeiro', 'Painel com o fluxo de energia em tempo real e Financeiro com receita, economia, gasto com a rede e distribuição do sol.'],
  painel: ['Energia em tempo real', 'Fluxo entre solar, bateria, rede, galeria e carregadores.'],
  fat: ['Faturamento', 'Receita das vagas e energia não comprada, por dia, mês e ano.'],
  gasto: ['Gasto com a rede', 'Custo da galeria e do eletroposto, créditos e economia do load shifting.'],
  consumo: ['Consumo solar e da rede', 'Hora a hora, por dia, semana, mês e ano: o que veio do sol e da bateria e o que foi comprado da rede.'],
  ev: ['Carregadores EV', 'Consumo do dia atendido por solar direto, bateria BESS e rede, com o rateio de 80% às vagas.'],
  dist: ['Distribuição da energia solar', 'Para onde foi o sol do dia, com receita e economia por destino.'],
  funil: ['Funil de vendas: Smart Home', 'Pela aba Casa, o motorista pode instalar em casa a solução residencial GoodWe que já existe e acompanhar geração solar, bateria e consumo.'],
  sus: ['Sustentabilidade', 'CO₂ evitado, árvores e km sem emissão, com a origem da energia.'],
  parc: ['Parceiros GoodWe', 'Credenciados para LEED e AQUA, levam a galeria a mais produtos GoodWe.'] };
const fit = (f, bw, bh) => { const [a, b] = dims(f); let w = bw, h = w * b / a; if (h > bh) { h = bh; w = h * a / b; } return [w, h]; };
// slide A: 3 + 2 células, imagem à esquerda e texto à direita
s = pres.addSlide({ masterName: 'Tela' });
header(s, '04', 'DIFERENCIAIS  ·  1 DE 4', 'Inteligência e funil de vendas', 'Diferenciais');
{ const GX = 0.15, bh = 1.78, TW = 1.45, IG = 0.1;
  const rows = [[['ia'], ['llm'], ['ls']], [['tarifa', 'modo'], ['funil', 'smart']]];
  rows.forEach((row, r) => {
    const cells = row.map(ks => { const ws = ks.map(k => fit('rect_' + k + '.png', ks.length > 1 ? 9 : 1.35, bh)); const iw = ws.reduce((a, [w]) => a + w, 0) + IG * (ks.length - 1); return { ks, ws, iw, w: iw + 0.14 + TW }; });
    const tot = cells.reduce((a, c) => a + c.w, 0) + GX * (cells.length - 1);
    let cx = (10 - tot) / 2; const cy = 1.22 + r * (bh + 0.16);
    cells.forEach(c => {
      let ix = cx;
      c.ks.forEach((k, n) => { const [w, h] = c.ws[n]; s.addImage({ path: 'rect_' + k + '.png', x: ix, y: cy + (bh - h) / 2, w, h, objectName: k + ' trecho do app', altText: DESC[c.ks[0]][0] }); ix += w + IG; });
      const k = c.ks[0];
      s.addText([{ text: DESC[k][0], options: { fontFace: FB, bold: true, fontSize: 12, color: T.brandStrong, breakLine: true } }, { text: DESC[k][1], options: { fontFace: F, fontSize: 9.5, color: T.mutedStrong } }],
        { x: cx + c.iw + 0.14, y: cy, w: TW, h: bh, margin: 0, valign: 'middle', paraSpaceAfter: 4, isTextBox: true, objectName: DESC[k][0] });
      cx += c.w + GX;
    });
  });
}
s.addNotes('Primeira parte dos diferenciais: IA como motor lógico com machine learning (Random Forest e K-Means), LLM com RAG no Síndico Virtual, tarifa dinâmica sobre a tarifa base do gestor (tarifa binômica, ponta e três modos de carregamento), load shifting preditivo e o funil de vendas: pela aba Casa, o motorista acessa o Smart Home e pode levar para casa a solução residencial que a GoodWe já tem, com geração solar, bateria e carregador.');
// slides B e C: grupos de telas lado a lado, legenda embaixo de cada grupo
const groupSlide = (pg, title, groups, bh, notes) => {
  const sl = pres.addSlide({ masterName: 'Tela' });
  header(sl, '04', 'DIFERENCIAIS  ·  ' + pg + ' DE 4', title, 'Diferenciais');
  const inner = 0.14, outer = 0.7;
  const G = groups.map(([keys, k]) => { const ws = keys.map(f => { const [a, b] = dims('rect_' + f + '.png'); return bh * a / b; }); return { keys, k, ws, w: ws.reduce((x, y) => x + y, 0) + inner * (ws.length - 1) }; });
  const total = G.reduce((x, g) => x + g.w, 0) + outer * (G.length - 1);
  let x = (10 - total) / 2;
  for (const g of G) {
    let ix = x;
    g.keys.forEach((f, j) => { sl.addImage({ path: 'rect_' + f + '.png', x: ix, y: 1.22, w: g.ws[j], h: bh, objectName: f + ' trecho do app', altText: DESC[g.k][0] }); ix += g.ws[j] + inner; });
    sl.addText([{ text: DESC[g.k][0], options: { fontFace: FB, bold: true, fontSize: 13.5, color: T.brandStrong, breakLine: true } }, { text: DESC[g.k][1], options: { fontFace: F, fontSize: 10, color: T.mutedStrong } }],
      { x: x + g.w / 2 - Math.min(Math.max(g.w, 3.0), g.w + outer - 0.15) / 2, y: 1.22 + bh + 0.1, w: Math.min(Math.max(g.w, 3.0), g.w + outer - 0.15), h: 3.86 - bh - 0.12, margin: 0, align: 'center', valign: 'top', paraSpaceAfter: 3, isTextBox: true, objectName: DESC[g.k][0] });
    x += g.w + outer;
  }
  sl.addNotes(notes);
};
groupSlide(2, 'Ecossistema, impacto e parceiros', [[['eco'], 'eco'], [['sus'], 'sus'], [['parc'], 'parc']], 2.85,
  'Segunda parte dos diferenciais: o ecossistema GoodWe no simulador, que soma cobertura solar, fachada BIPV, carport e baterias; o impacto ambiental da galeria, com CO₂ evitado e equivalentes; e os parceiros GoodWe, que estimulam a eficiência energética, somam créditos LEED e AQUA e levam a galeria a mais produtos da marca.');
groupSlide(3, 'Dashboards de energia', [[['painel'], 'painel'], [['consumo'], 'consumo'], [['ev'], 'ev']], 2.85,
  'Terceira parte dos diferenciais: os dashboards de energia do gestor. O Painel mostra o fluxo de energia em tempo real; ao expandir Consumo solar e da rede por período aparecem o consumo hora a hora por dia, semana, mês e ano e o destino do sol consumido; ao expandir Carregadores EV aparece de onde veio a energia das vagas no dia: solar direto, bateria BESS e rede, seguindo o rateio que reserva 80% da geração às vagas.');
groupSlide(4, 'Dashboards financeiros', [[['fat'], 'fat'], [['gasto'], 'gasto'], [['dist'], 'dist']], 2.85,
  'Quarta parte dos diferenciais: os dashboards financeiros. Ao expandir Faturamento aparecem o total do período, o faturado, o economizado e a receita por hora; ao expandir Gasto com energia da rede aparecem o custo por galeria e eletroposto, os créditos de exportação e a economia potencial com load shifting; a Distribuição da energia solar mostra, por destino, a receita e a economia geradas pelo sol do dia.');
// ---------- agradecimento: foto (ou iniciais) em círculo + nome + breve descritivo
{
  const sl = pres.addSlide(); sl.background = { path: 's_obrigado.png' };
  sl.addText('ECOVOLTS  ·  TURMA CCPW  ·  EQUIPE 4', { x: 0.5, y: 0.75, w: 9, h: 0.24, fontFace: FX, bold: true, fontSize: 10, color: T.brandStrong, charSpacing: 1.5, align: 'center', margin: 0, isTextBox: true, objectName: 'Equipe' });
  { const t = titleImg('Obrigado!', T.brand, 50); sl.addImage({ path: t.path, x: (10 - t.w) / 2, y: 1.07 + (0.9 - t.h) / 2, w: t.w, h: t.h, objectName: 'Obrigado', altText: 'Obrigado!' }); }
  const BIO = { // breve descritivo de cada integrante (editar aqui)
    '572899': 'Scrum Master', '571836': 'Desenvolvedora', '571562': 'Desenvolvedora e Product Owner',
    '570436': 'Desenvolvedor', '572395': 'Desenvolvedor', '570540': 'Desenvolvedor' };
  const col = 1.5, d = 1.12, x0 = (10 - col * team.length) / 2, yc = 2.35;
  team.forEach(([rm, n], i) => {
    const cx = x0 + col * i + col / 2;
    sl.addImage({ path: 'av_' + rm + '.png', x: cx - d / 2, y: yc, w: d, h: d, objectName: n + ' foto', altText: 'Foto de ' + n });
    sl.addText(n, { x: cx - col / 2 + 0.05, y: yc + d + 0.14, w: col - 0.1, h: 0.46, fontFace: FB, bold: true, fontSize: 11, color: T.ink, align: 'center', valign: 'top', margin: 0, isTextBox: true, objectName: n });
    sl.addText([{ text: BIO[rm], options: { color: T.brandStrong, bold: true, breakLine: true } }, { text: 'RM ' + rm, options: { color: T.muted } }],
      { x: cx - col / 2 + 0.05, y: yc + d + 0.62, w: col - 0.1, h: 0.7, fontFace: F, fontSize: 9.5, align: 'center', valign: 'top', margin: 0, isTextBox: true, objectName: n + ' descritivo' });
  });
  sl.addText([{ text: 'ChargeGrid', options: { fontFace: FB, bold: true, color: T.brand } }, { text: '  Intelligence', options: { fontFace: F, color: T.mutedStrong } }, { text: '  |  ', options: { fontFace: F, color: T.borderStrong } }, { text: 'Ecovolts', options: { fontFace: FB, bold: true, color: '4E9A06' } }],
    { x: 0.45, y: 5.26, w: 2.8, h: 0.22, fontSize: 9.5, margin: 0, valign: 'middle', isTextBox: true, objectName: 'Marca' });
  sl.addNotes('Agradecemos à GoodWe e à FIAP. Equipe Ecovolts, turma CCPW, equipe 4.');
}
await pres.writeFile({ fileName: 'ChargeGrid-Sprint4.pptx' }); await applyTheme('ChargeGrid-Sprint4.pptx', THEME); console.log('ok');
})();
