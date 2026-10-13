// ---- contexto do app para o assistente de IA -------------------------------
// O modelo de ML roda no navegador (src/ml/previsao-motor.js). Para o LLM não
// inventar números, o app manda junto com cada pergunta um "snapshot" com os
// números que as ferramentas do agente vão consultar
// (supabase/functions/assistente/ferramentas.ts). Em produção, os mesmos campos
// viriam das tabelas do Supabase (leituras_energia, recargas, carregadores).
//
// Funções puras: recebem MLPrev e o estado já resumido, devolvem JSON simples.
const SnapshotIA = (() => {
  const r1 = (v) => Math.round(v * 10) / 10;
  const r0 = (v) => Math.round(v);

  const dia = (M, d, cen) => {
    const e = M.preverDia('ev', d, cen), g = M.preverDia('galeria', d, cen);
    const b = M.balanco(d, cen);
    const cal = M.D.calendario[d];
    const pico = (hs) => hs.reduce((a, v, h) => (v > hs[a] ? h : a), 0);
    const ivE = M.iv('ev'), ivG = M.iv('galeria');
    return {
      d, quando: M.quandoDia(d), data: cal.data,
      feriado: cal.feriado ? cal.nome_feriado : null, data_comercial: cal.data_comercial || null,
      horario_galeria: cal.abre + 'h-' + cal.fecha + 'h', horario_eletroposto: cal.ep_abre + 'h-' + cal.ep_fecha + 'h',
      eletroposto_kwh: r0(e.total), eletroposto_margem_kwh: r0(e.total * ivE.dia_q80_rel), eletroposto_pico_h: pico(e.horas),
      galeria_kwh: r0(g.total), galeria_margem_kwh: r0(g.total * ivG.dia_q80_rel), galeria_pico_h: pico(g.horas),
      energia: {
        necessaria_kwh: r0(b.need), solar_gerada_kwh: r0(b.sol), solar_usada_kwh: r0(b.solUso),
        bateria_entregue_kwh: r0(b.bat), rede_kwh: r0(b.rede), rede_ponta_kwh: r0(b.redePonta),
        exportada_kwh: r0(b.exp), compra_madrugada_kwh: r0(b.compra),
        bateria_cheia_as: b.cheiaAs == null ? null : b.cheiaAs + 'h', custo_rede_rs: r0(b.custo),
        solar_para_eletroposto_kwh: r0(b.solEv), solar_para_galeria_kwh: r0(b.solGal),
      },
      fatores_eletroposto: M.explicarDia('ev', d, cen).slice(0, 3).map(f => ({ fator: f.label, kwh: r1(f.kwh) })),
      fatores_galeria: M.explicarDia('galeria', d, cen).slice(0, 3).map(f => ({ fator: f.label, kwh: r1(f.kwh) })),
    };
  };

  // histórico medido (últimas semanas): totais por dia e perfil médio por hora
  const historico = (M, dias = 28) => {
    const H = M.D.historico, n = Math.floor(H.ev.length / 24), ini = Math.max(0, n - dias);
    const br = (d) => d.slice(8, 10) + '/' + d.slice(5, 7);
    const DS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
    const d0 = new Date(H.inicio);
    const porDia = [], ev = Array(24).fill(0), gal = Array(24).fill(0);
    for (let d = ini; d < n; d++) {
      const e = H.ev.slice(d * 24, d * 24 + 24), g = H.galeria.slice(d * 24, d * 24 + 24);
      e.forEach((v, h) => { ev[h] += v / (n - ini); });
      g.forEach((v, h) => { gal[h] += v / (n - ini); });
      const dt = new Date(d0.getTime() + d * 86400000);
      porDia.push({ data: dt.toISOString().slice(0, 10), dia_semana: DS[dt.getDay()], eletroposto_kwh: r0(e.reduce((a, b) => a + b, 0)), galeria_kwh: r0(g.reduce((a, b) => a + b, 0)) });
    }
    const top = (arr) => arr.map((v, h) => ({ h, v })).sort((a, b) => b.v - a.v).slice(0, 3).map(x => ({ hora: x.h + 'h', kwh_medio: r1(x.v) }));
    return {
      periodo: br(porDia[0].data) + ' a ' + br(porDia[porDia.length - 1].data) + ', ' + porDia.length + ' dias medidos',
      eletroposto_horas_mais_carregamento: top(ev),
      galeria_horas_mais_consumo: top(gal),
      eletroposto_kwh_medio_por_hora: ev.map(r1),
      ultimos_dias: porDia.slice(-14),
    };
  };

  const sindico = (M, cen, extra) => {
    const n = M.dias();
    const dias = [];
    for (let d = 0; d < n; d++) dias.push(dia(M, d, cen));
    const ls = [];
    for (let d = 0; d < n; d++) M.loadShift(d, cen).forEach(x => ls.push({
      quando: M.quandoDia(d), titulo: x.titulo, kwh: r0(x.kwh), de: x.de, para: x.para, economia_rs: r1(x.econ),
    }));
    const an = M.analiseDia(0, cen);
    const rs = M.resumoSemana(cen);
    return {
      papel: 'sindico', galeria: extra.galeria || 'Galeria Pátio Norte',
      tarifas_rede: { ponta_rs_kwh: 1.5, fora_ponta_rs_kwh: 0.85, credito_exportacao_rs_kwh: 0.6, ponta: '17h-21h' },
      regra_rateio: 'Com a galeria aberta, até 80% do sol vai para o eletroposto; sobra de sol nunca é trocada por energia da rede.',
      previsao: dias,
      semana: {
        eletroposto_kwh: r0(dias.reduce((a, x) => a + x.eletroposto_kwh, 0)),
        galeria_kwh: r0(dias.reduce((a, x) => a + x.galeria_kwh, 0)),
        margem_semana_rel: M.iv('ev').semana_q80_rel,
        pico_rede_kw: r1(rs.pico.rede), pico_quando: M.quandoDia(rs.pico.d) + ' ' + rs.pico.h + 'h',
        pico_pct_teto: r0(rs.pct * 100), teto_operacional_kw: M.LIMITE,
      },
      alertas: M.alertas(cen).map(a => ({ severidade: a.sev, titulo: a.titulo, quando: a.quando, acao: a.acao })),
      load_shifting: ls,
      ampliacao_bateria: {
        recomendado: !!an.bateria.ok, titulo: an.bateria.titulo, resumo: an.bateria.valor, texto: an.bateria.texto,
        opcoes: (an.bateria.opcoes || []).map(o => ({ opcao: o.rotulo, economia: o.econ, investimento: o.inv, retorno: o.payback })),
      },
      historico: historico(M),
      hoje_ate_agora: extra.hoje || null,
      vagas: extra.vagas || [],
      tarifa: extra.tarifa || null,
      faturamento: extra.faturamento || null,
    };
  };

  const motorista = (extra) => ({ papel: 'motorista', ...extra });

  return { sindico, motorista, dia, historico };
})();
