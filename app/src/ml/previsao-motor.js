// ---- motor de previsão (machine learning) --------------------------------
// Roda no app os Random Forests treinados no notebook inteligencia/ChargeGrid_ML.ipynb
// (lógica das aulas de SERS) e exportados para ML_DADOS (src/ml/previsao-dados.js).
// Nada aqui é regra fixa: o número sai do modelo.
//
// As variáveis são montadas exatamente como em inteligencia/variaveis.py —
// inteligencia/testar_paridade_js.py compara as duas pontas.
//
// Em produção: ML_DADOS.historico viria de leituras_energia + MeterValues
// OCPP no Supabase, e ML_DADOS.futuro da API Open-Meteo; a inferência pode
// continuar aqui ou ir para uma Edge Function sem mudar a interface abaixo.
const MLPrev = (() => {
  const D = ML_DADOS;
  const NH = D.historico.ev.length;              // 1008 h = 6 semanas
  const DSEM = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
  const DSEM_LONGO = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'];
  const LIMITE = D.contratadaKw * (1 - D.margemDlm);
  const PONTA = [17, 21];
  const r1 = (v) => Math.round(v * 10) / 10;

  // ---- Random Forest: média das folhas de todas as árvores
  // (mesma regra do sklearn: x <= limiar vai para a esquerda; o sklearn compara
  // a entrada convertida para float32, daí o Math.fround)
  const avaliar = (m, x0) => {
    const x = x0.map(v => Math.fround(v));
    let soma = 0;
    for (let i = 0; i < m.arvores.length; i++) {
      const a = m.arvores[i];
      let n = 0;
      while (a.f[n] !== -1) {
        const v = x[a.f[n]];
        n = (v !== v) ? (a.m[n] ? a.l[n] : a.r[n]) : (v <= a.t[n] ? a.l[n] : a.r[n]);
      }
      soma += a.v[n];
    }
    return soma / m.arvores.length;
  };

  const serie = { ev: D.historico.ev, galeria: D.historico.galeria };
  // j: índice no tempo (histórico + futuro). null no histórico = hora sem medição
  const y = (alvo, j) => { const v = j >= 0 && j < NH ? serie[alvo][j] : null; return v == null ? NaN : v; };
  const media = (vals, minimo = 1) => {
    let s = 0, n = 0;
    vals.forEach(v => { if (v === v) { s += v; n++; } });
    return n >= minimo ? s / n : NaN;
  };
  // mesma hora nas 4 semanas anteriores, ignorando horas sem medição (variaveis.media_4sem)
  const media4 = (alvo, j) => {
    return media([y(alvo, j - 168), y(alvo, j - 336), y(alvo, j - 504), y(alvo, j - 672)]);
  };
  // nível recente do eletroposto: média das media4 nas últimas 168 h (variaveis.nivel_ev)
  const nivelEv = (j) => {
    const v = [];
    for (let k = j - 167; k <= j; k++) v.push(media4('ev', k));
    const c = media(v, 24);
    return c === c ? Math.max(D.modelos.ev.nivelMin || 0.3, c) : NaN;
  };

  const horarioPadrao = (dow) => (dow === 6
    ? { abre: 12, fecha: 20, ep_abre: 12, ep_fecha: 20 }
    : { abre: 10, fecha: 22, ep_abre: 10, ep_fecha: 21 });

  // clima do dia d (0..6) com o cenário aplicado
  const climaDia = (d, cen) => {
    const F = D.futuro, N = D.normais, o = d * 24, c = {};
    ['temperatura', 'irradiancia', 'nebulosidade', 'precipitacao', 'umidade'].forEach(k => {
      c[k] = F[k].slice(o, o + 24);
    });
    if (cen.tempNormal) { c.temperatura = N.temperatura.slice(); c.umidade = N.umidade.slice(); }
    if (cen.solNormal) { c.irradiancia = N.irradiancia.slice(); c.nebulosidade = N.nebulosidade.slice(); }
    if (cen.semChuva) c.precipitacao = c.precipitacao.map(() => 0);
    if (cen.tempDelta) c.temperatura = c.temperatura.map(v => r1(v + cen.tempDelta));
    return c;
  };

  const calDia = (d, cen) => {
    let c = { ...D.calendario[d] };
    if (cen.semFeriado) {
      c = { ...c, feriado: 0, vespera_feriado: 0, ponte: 0, fator_comercial: 1, ...horarioPadrao(c.dia_semana) };
    }
    if (cen.dow != null) c = { ...c, dia_semana: cen.dow, ...(c.feriado ? {} : horarioPadrao(cen.dow)) };
    return c;
  };

  // as mesmas colunas de variaveis.py, na mesma ordem do modelo
  const featuresHora = (alvo, d, h, cen, cl, cal) => {
    const j = NH + d * 24 + h;
    const m = D.modelos[alvo];
    const v = {
      temperatura_c: cl.temperatura[h], umidade_pct: cl.umidade[h], nuvens_pct: cl.nebulosidade[h],
      irradiancia_w_m2: cl.irradiancia[h], chuva_mm: cl.precipitacao[h],
      hora: h, dia_semana: cal.dia_semana, feriado: cal.feriado, fator_comercial: cal.fator_comercial,
      galeria_aberta: h >= cal.abre && h < cal.fecha ? 1 : 0,
      eletroposto_aberto: h >= cal.ep_abre && h < cal.ep_fecha ? 1 : 0,
      vagas_operando: cen.vagas != null ? cen.vagas : 4,
      media_4sem_galeria_kwh: media4('galeria', j), media_4sem_ev_kwh: media4('ev', j),
    };
    return { x: m.features.map(f => v[f]), escala: m.escala === 'nivel_ev' ? nivelEv(j) : 1 };
  };

  const cache = {};
  const preverDia = (alvo, d, cen = {}) => {
    const key = alvo + d + JSON.stringify(cen);
    if (cache[key]) return cache[key];
    const cl = climaDia(d, cen), cal = calDia(d, cen), m = D.modelos[alvo];
    const horas = [];
    for (let h = 0; h < 24; h++) {
      const f = featuresHora(alvo, d, h, cen, cl, cal);
      horas.push(Math.max(0, avaliar(m, f.x) * f.escala));
    }
    const total = horas.reduce((a, b) => a + b, 0);
    return (cache[key] = { horas, total, clima: cl, cal });
  };

  const solarDia = (d, cen = {}) => {
    const cl = climaDia(d, cen);
    return cl.irradiancia.map((g, h) => {
      const tc = cl.temperatura[h] + 0.03 * g;
      return Math.max(0, D.kSolar * g * (1 - 0.004 * (tc - 25)));
    });
  };

  // ---- balanço de energia do dia: quanto é preciso e de onde vem
  // Mesma lógica de despacho do simulador (inteligencia/gerar_base_simulada.py):
  // o sol atende primeiro o consumo da hora; a sobra carrega a bateria e o resto
  // é exportado; na ponta (17h–21h) a bateria descarrega achatando o pico; o
  // que faltar vem da rede. opt.preCarga compra da rede entre 03h e 06h;
  // opt.mover desloca kWh de carga da ponta para as horas de sobra solar.
  const TARIFA = { ponta: 1.50, fora: 0.85 };   // R$/kWh, as mesmas do Síndico
  const CREDITO_EXPORT = 0.60;                  // R$/kWh injetado (compensação, estimativa já sem o Fio B)
  const EF = 0.95;                              // eficiência de carga e de descarga do BESS
  const BAT_MIN = D.bessKwh * 0.10;
  const CARGA_REDE_KW = 10;                     // compra fora de ponta, como no simulador
  const ehPonta = (h) => h >= PONTA[0] && h < PONTA[1];
  // regra de negócio do rateio: com a galeria aberta, o sol atende PRIMEIRO o eletroposto,
  // até 80% da geração; o restante vai para a galeria; só o que ainda sobrar carrega a
  // bateria ou é exportado. É prioridade, não teto: nunca se compra da rede com sol sobrando.
  // A bateria também atende primeiro o eletroposto. Com a galeria fechada, o sol atende quem
  // estiver consumindo.
  const RATEIO_EV = 0.8;
  const ratear = (sol, gal, ev, aberta) => {
    if (aberta) {
      let sEv = Math.min(ev, sol * RATEIO_EV);
      const sGal = Math.min(gal, sol - sEv);
      sEv += Math.min(ev - sEv, sol - sEv - sGal);          // sobra depois da galeria volta às vagas
      return { sEv, sGal };
    }
    const sGal = Math.min(gal, sol);
    return { sGal, sEv: Math.min(ev, sol - sGal) };
  };
  const tarifaHora = (h) => (ehPonta(h) ? TARIFA.ponta : TARIFA.fora);
  const cacheB = {};

  // tira kWh da ponta (proporcional ao que a carga puxa da rede ali) e põe nas horas de sobra
  const deslocar = (horas, kwh, origem, destino) => {
    const out = horas.slice();
    const so = origem.reduce((a, x) => a + x.peso, 0), sd = destino.reduce((a, x) => a + x.peso, 0);
    if (so <= 0 || sd <= 0) return out;
    origem.forEach(x => { out[x.h] = Math.max(0, out[x.h] - kwh * x.peso / so); });
    destino.forEach(x => { out[x.h] += kwh * x.peso / sd; });
    return out;
  };

  const balanco = (d, cen = {}, opt = {}) => {
    const key = d + JSON.stringify(cen) + JSON.stringify(opt);
    if (cacheB[key]) return cacheB[key];
    let ev = preverDia('ev', d, cen).horas, gal = preverDia('galeria', d, cen).horas;
    const sol = solarDia(d, cen);
    const cal = D.calendario[d];
    if (opt.mover) {
      const b0 = balanco(d, cen);
      const exp = b0.linhas.map(x => x.exp);
      if (opt.mover.ev) {
        ev = deslocar(ev, opt.mover.ev,
          b0.linhas.filter(x => x.ponta && x.rede > 0 && x.ev > 0).map(x => ({ h: x.h, peso: x.rede * x.ev / x.need })),
          b0.linhas.filter(x => x.h >= cal.ep_abre && x.h < cal.ep_fecha && exp[x.h] > 0).map(x => ({ h: x.h, peso: exp[x.h] })));
      }
      if (opt.mover.gal) {
        gal = deslocar(gal, opt.mover.gal,
          b0.linhas.filter(x => x.ponta && x.rede > 0).map(x => ({ h: x.h, peso: x.rede * x.gal / x.need })),
          b0.linhas.filter(x => x.h >= 12 && x.h < PONTA[0] && exp[x.h] > 0).map(x => ({ h: x.h, peso: exp[x.h] })));
      }
    }
    // opt.bess: bateria hipotética { kwh, kw } (ampliação); sem ela, a bateria instalada
    const CAP = opt.bess ? opt.bess.kwh : D.bessKwh, PKW = opt.bess ? opt.bess.kw : D.bessKw, MIN = CAP * 0.10;
    let soc = d === 0 ? MIN : balanco(d - 1, cen, opt.bess ? { bess: opt.bess } : {}).socFim;
    let cheiaAs = null;
    // compra de madrugada só até deixar espaço para a sobra solar prevista antes da ponta
    const aberta = (h) => h >= cal.abre && h < cal.fecha;
    const rat = sol.map((g, h) => ratear(g, gal[h], ev[h], aberta(h)));
    let sobraPrev = 0; for (let h = 0; h < PONTA[0]; h++) sobraPrev += Math.max(0, sol[h] - rat[h].sEv - rat[h].sGal);
    const alvoCompra = Math.max(MIN, CAP - Math.min(PKW * 6, sobraPrev) * EF);
    const socIni = soc;
    const dis = new Array(24).fill(0);
    const linhas = [];
    let soc17 = soc;
    for (let h = 0; h < 24; h++) {
      const need = gal[h] + ev[h];
      const { sEv, sGal } = rat[h];
      const solUso = sEv + sGal, sobra = sol[h] - solUso;
      if (h === PONTA[0]) {
        // descarga achatando o pico: nível de corte que gasta a energia útil da bateria
        soc17 = soc;
        const orc = Math.max(0, soc - MIN) * EF;
        const def = []; for (let k = PONTA[0]; k < PONTA[1]; k++) def.push(Math.max(0, gal[k] + ev[k] - rat[k].sEv - rat[k].sGal));
        const gasto = (nv) => def.reduce((a, x) => a + Math.min(PKW, Math.max(0, x - nv)), 0);
        let lo = 0, hi = Math.max(0, ...def);
        if (gasto(0) <= orc) hi = 0;
        else for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; if (gasto(m) > orc) lo = m; else hi = m; }
        def.forEach((x, k) => { dis[PONTA[0] + k] = Math.min(PKW, Math.max(0, x - hi)); });
      }
      const espaco = Math.max(0, CAP - soc) / EF;
      let cargaRede = 0, cargaSol = 0;
      if (opt.preCarga && h >= 3 && h < 6) cargaRede = Math.min(CARGA_REDE_KW * CAP / D.bessKwh, Math.max(0, alvoCompra - soc) / EF);
      else if (sobra > 0) cargaSol = Math.min(PKW, sobra, espaco);
      soc += (cargaRede + cargaSol) * EF - dis[h] / EF;
      if (cheiaAs == null && h < PONTA[0] && soc >= CAP - 0.3) cheiaAs = h;
      const rede = Math.max(0, need - solUso - dis[h] + cargaRede);
      const disEv = Math.min(dis[h], Math.max(0, ev[h] - sEv)), disGal = dis[h] - disEv;   // bateria: eletroposto primeiro
      linhas.push({ h, ponta: ehPonta(h), aberta: aberta(h), gal: gal[h], ev: ev[h], need, sol: sol[h], solUso, solEv: sEv, solGal: sGal,
        cargaSol, cargaRede, dis: dis[h], disEv, disGal,
        redeEv: Math.max(0, ev[h] - sEv - disEv), redeGal: Math.max(0, gal[h] - sGal - disGal),
        exp: sobra - cargaSol, rede, soc, liq: need - sol[h] });
    }
    const S = (k, f = () => true) => linhas.filter(f).reduce((a, x) => a + x[k], 0);
    const t = {
      linhas, socIni, soc17, socFim: soc, cap: CAP, cheiaAs,
      gal: S('gal'), ev: S('ev'), need: S('need'), sol: S('sol'), solUso: S('solUso'), solEv: S('solEv'), solGal: S('solGal'), solBat: S('cargaSol'),
      disEv: S('disEv'), disGal: S('disGal'), redeEv: S('redeEv'), redeGal: S('redeGal'),
      bat: S('dis'), exp: S('exp'), compra: S('cargaRede'), rede: S('rede'),
      redePonta: S('rede', x => x.ponta), redeFora: S('rede', x => !x.ponta),
      pontaNeed: S('need', x => x.ponta),
    };
    t.custo = linhas.reduce((a, x) => a + x.rede * tarifaHora(x.h) - x.exp * CREDITO_EXPORT, 0);
    return (cacheB[key] = t);
  };

  // demanda prevista na rede hora a hora (kW médio da hora; negativo = exportação)
  const redeDia = (d, cen = {}, opt = {}) => balanco(d, cen, opt).linhas.map(x => ({
    ...x, bess: x.dis, rede: x.need + x.cargaSol + x.cargaRede - x.sol - x.dis,
  }));

  // ---- load-shifting: só recomenda quando o cenário deslocado sai mais barato
  // (comparação dos dois balanços, com tarifa de ponta e crédito de exportação)
  const ECON_MIN = 3;   // R$/dia: abaixo disso não vale o esforço operacional
  const loadShift = (d, cen = {}) => {
    const b = balanco(d, cen);
    const out = [];
    const faixaH = (hs) => (hs.length ? String(hs[0]).padStart(2, '0') + 'h–' + String(hs[hs.length - 1] + 1).padStart(2, '0') + 'h' : '');
    // 1) pré-carga da bateria fora de ponta
    if (b.redePonta > 1 && b.soc17 < D.bessKwh * 0.95) {
      const a = balanco(d, cen, { preCarga: true });
      const econ = b.custo - a.custo;
      if (econ >= ECON_MIN) out.push({
        tipo: 'precarga', opt: { preCarga: true }, econ, kwh: a.compra, de: '03h–06h', para: 'ponta 17h–21h',
        titulo: 'Carregar a bateria com a rede de madrugada',
        texto: 'O sol deixa a bateria em ' + Math.round(b.soc17 / D.bessKwh * 100) + '% às 17h. Comprar ' + Math.round(a.compra) + ' kWh entre 03h e 06h (R$ '
          + TARIFA.fora.toFixed(2).replace('.', ',') + '/kWh) tira ' + Math.round(b.redePonta - a.redePonta) + ' kWh da ponta (R$ ' + TARIFA.ponta.toFixed(2).replace('.', ',') + '/kWh).',
        pico: Math.max(...redeDia(d, cen).map(x => x.rede)) - Math.max(...redeDia(d, cen, { preCarga: true }).map(x => x.rede)),
      });
    }
    // 2) recarga dos carros: da ponta para as horas de sol sobrando
    const cal = D.calendario[d];
    const evPontaRede = b.linhas.filter(x => x.ponta && x.need > 0).reduce((a, x) => a + x.rede * x.ev / x.need, 0);
    const destEv = b.linhas.filter(x => x.h >= cal.ep_abre && x.h < cal.ep_fecha && x.exp > 0.2).map(x => x.h);
    const expEv = destEv.reduce((a, h) => a + b.linhas[h].exp, 0);
    const moverEv = Math.min(evPontaRede, expEv) * 0.5;   // metade: quanto se espera que a tarifa consiga deslocar
    if (moverEv >= 2) {
      const a = balanco(d, cen, { mover: { ev: moverEv } });
      const econ = b.custo - a.custo;
      if (econ >= ECON_MIN) out.push({
        tipo: 'ev', opt: { mover: { ev: moverEv } }, econ, kwh: moverEv, de: 'ponta 17h–21h', para: faixaH(destEv),
        titulo: 'Puxar a recarga dos carros para o horário de sol',
        texto: 'As vagas devem puxar ' + Math.round(evPontaRede) + ' kWh da rede na ponta enquanto ' + Math.round(expEv) + ' kWh de sol sobram das ' + faixaH(destEv)
          + '. Desconto α solar maior nessas horas e acréscimo na ponta podem deslocar cerca de ' + Math.round(moverEv) + ' kWh (metade do possível).',
      });
    }
    // 3) climatização da galeria: pré-resfriar antes da ponta em dia quente com sol sobrando
    const tmax = Math.max(...climaDia(d, cen).temperatura);
    const galPontaRede = b.linhas.filter(x => x.ponta && x.need > 0).reduce((a, x) => a + x.rede * x.gal / x.need, 0);
    const destGal = b.linhas.filter(x => x.h >= 12 && x.h < PONTA[0] && x.exp > 0.2).map(x => x.h);
    const expGal = destGal.reduce((a, h) => a + b.linhas[h].exp, 0) - (out.find(r => r.tipo === 'ev') || { kwh: 0 }).kwh;
    const moverGal = Math.min(galPontaRede * 0.12, Math.max(0, expGal));   // inércia térmica: ~12% da climatização da ponta
    if (tmax >= 26 && moverGal >= 2) {
      const a = balanco(d, cen, { mover: { gal: moverGal } });
      const econ = b.custo - a.custo;
      if (econ >= ECON_MIN) out.push({
        tipo: 'gal', opt: { mover: { gal: moverGal } }, econ, kwh: moverGal, de: 'ponta 17h–21h', para: faixaH(destGal),
        titulo: 'Pré-resfriar a galeria antes da ponta',
        texto: 'Dia de ' + virg(tmax) + ' °C com sol sobrando das ' + faixaH(destGal) + ': baixar o setpoint da climatização em 1 a 2 °C nessas horas e subir na ponta desloca cerca de '
          + Math.round(moverGal) + ' kWh.',
      });
    }
    return out.sort((x, z) => z.econ - x.econ);
  };


  // ---- Síndico Virtual lendo o gráfico do dia: explica e recomenda
  // (comprar energia fora de ponta? ampliar a bateria para guardar o sol que sobra?)
  // Premissas da ampliação: R$ 2.500 por kWh instalado (BESS LFP comercial) e potência de 0,5C.
  const CUSTO_BESS_KWH = 2500;
  const AMPLIACOES = [30, 60, 90];
  const analiseDia = (d, cen = {}) => {
    const b = balanco(d, cen);
    const hh2 = (h) => String(h).padStart(2, '0') + 'h';
    const L = b.linhas;
    const sobra = L.filter(x => x.sol - x.solUso > 0.3).map(x => x.h);
    const faixaS = sobra.length ? hh2(sobra[0]) + ' e ' + hh2(sobra[sobra.length - 1] + 1) : '';
    const picoRede = L.filter(x => x.ponta).reduce((a, x) => (x.rede > a.rede ? x : a));
    const R = (v) => (Math.round(v) || 0).toLocaleString('pt-BR');
    const leitura = [];
    if (sobra.length) leitura.push('Entre ' + faixaS + ' o sol passa do consumo (vagas primeiro, depois a galeria) e sobram ' + R(b.solBat + b.exp) + ' kWh. A bateria de ' + R(b.cap) + ' kWh guarda só '
      + R(b.solBat) + (b.cheiaAs != null ? ' e fica cheia às ' + hh2(b.cheiaAs + 1) : '') + '; os outros ' + R(b.exp) + ' kWh vão para a rede valendo cerca de R$ ' + CREDITO_EXPORT.toFixed(2).replace('.', ',') + '/kWh.');
    else leitura.push('O sol não chega a passar do consumo em nenhuma hora: tudo o que as placas geram (' + R(b.sol) + ' kWh) é usado na hora ou guardado.');
    leitura.push('Na ponta (17h–21h) a bateria entrega ' + R(b.bat) + ' kWh e a rede ' + R(b.redePonta) + ' kWh a R$ 1,50/kWh, com pico de ' + virg(picoRede.rede) + ' kW às ' + hh2(picoRede.h)
      + ' (' + Math.round(picoRede.rede / LIMITE * 100) + '% do teto do DLM).');

    // 1) comprar energia fora de ponta
    const pc = balanco(d, cen, { preCarga: true });
    const econPc = b.custo - pc.custo;
    const compra = econPc >= ECON_MIN
      ? { ok: true, titulo: 'Comprar energia de madrugada', valor: 'R$ ' + R(econPc) + '/dia',
          texto: 'Carregar ' + R(pc.compra) + ' kWh da rede entre 03h e 06h (R$ 0,85/kWh) e descarregar na ponta tira ' + R(b.redePonta - pc.redePonta) + ' kWh da tarifa de R$ 1,50.' }
      : { ok: false, titulo: 'Comprar energia de madrugada', valor: econPc > 0.5 ? 'R$ ' + R(econPc) + '/dia' : 'sem ganho',
          texto: b.soc17 >= b.cap * 0.95
            ? 'Não compensa hoje: a sobra de sol já enche a bateria antes da ponta, então a energia comprada só tomaria o lugar da solar.'
            : 'Não compensa hoje: o ganho seria menor que R$ ' + ECON_MIN + ' no dia.' };

    // 2) ampliar a bateria: mesma semana prevista com mais capacidade (potência 0,5C)
    const nD = D.calendario.length;
    const custoDia = (k, bess) => Math.min(balanco(k, cen, bess ? { bess } : {}).custo, balanco(k, cen, bess ? { bess, preCarga: true } : { preCarga: true }).custo);
    const custoSem = (bess) => { let c = 0; for (let k = 0; k < nD; k++) c += custoDia(k, bess); return c; };
    const base = custoSem(null);
    const opcoes = AMPLIACOES.map(extra => {
      const kwh = D.bessKwh + extra, bess = { kwh, kw: Math.max(D.bessKw, kwh * 0.5) };
      const econDia = (base - custoSem(bess)) / nD;
      const inv = extra * CUSTO_BESS_KWH;
      const b1 = balanco(d, cen, { bess }), b2 = balanco(d, cen, { bess, preCarga: true });
      const bd = b2.custo < b1.custo ? b2 : b1;
      let diasCompra = 0; for (let k = 0; k < nD; k++) if (balanco(k, cen, { bess, preCarga: true }).custo < balanco(k, cen, { bess }).custo - ECON_MIN) diasCompra++;
      return { extra, kwh, econDia, econAno: econDia * 365, inv, payback: econDia > 0 ? inv / (econDia * 365) : Infinity,
        hojeRedePonta: bd.redePonta, hojeExp: bd.exp, hojeEcon: b.custo - bd.custo, hojeCompra: bd.compra, diasCompra };
    });
    const melhor = opcoes.reduce((a, o) => (o.payback < a.payback ? o : a));
    if (!compra.ok && melhor.diasCompra) compra.texto += ' Com a bateria ampliada para ' + melhor.kwh + ' kWh, a compra de madrugada passa a compensar em ' + melhor.diasCompra + ' dos ' + nD + ' dias da semana (os mais nublados).';
    const anos = (p) => (p === Infinity ? '—' : virg(p, 1) + ' anos');
    const vale = melhor.payback <= 8;   // vida útil típica de LFP: ~10 anos; folga para degradação
    const bateria = {
      ok: vale, titulo: 'Ampliar a bateria em ' + melhor.extra + ' kWh', valor: 'retorno em ' + anos(melhor.payback),
      texto: 'Com ' + melhor.kwh + ' kWh a bateria guarda mais sol de manhã' + (melhor.hojeCompra > 0.5 ? ' e, como hoje o sol não basta, completa com ' + R(melhor.hojeCompra) + ' kWh comprados de madrugada' : '')
        + ': a rede na ponta cairia de ' + R(b.redePonta) + ' para ' + R(melhor.hojeRedePonta) + ' kWh e a exportação de ' + R(b.exp) + ' para ' + R(melhor.hojeExp) + ' kWh. Na semana prevista, economia média de R$ ' + R(melhor.econDia) + '/dia (≈ R$ '
        + R(melhor.econAno) + '/ano) para um investimento de R$ ' + R(melhor.inv) + '.'
        + (vale ? '' : ' Retorno longo para a vida útil de uma bateria LFP (~10 anos). Passa a compensar (retorno em 8 anos) se o kWh instalado sair abaixo de R$ '
          + R(melhor.econAno * 8 / melhor.extra) + ', ou com mais carga na ponta.'),
      opcoes: opcoes.map(o => ({ rotulo: '+' + o.extra + ' kWh', econ: 'R$ ' + R(o.econAno) + '/ano', inv: 'R$ ' + R(o.inv), payback: anos(o.payback), melhor: o === melhor })),
    };
    const resumo = vale
      ? 'Minha recomendação: guardar o sol em vez de exportar. Ampliar a bateria em ' + melhor.extra + ' kWh se paga em ' + anos(melhor.payback) + '.'
      : 'Minha recomendação: por enquanto, deslocar carga para as horas de sol; ampliar a bateria ainda tem retorno longo (' + anos(melhor.payback) + ').';
    const ui = {
      veredito: vale ? 'Vale ampliar a bateria em ' + melhor.extra + ' kWh' : (b.exp > 5 ? 'Use o sol que sobra antes de comprar bateria' : 'Dia sem sobra de sol relevante'),
      frase: b.cheiaAs != null && b.exp > 5
        ? 'A bateria enche às ' + hh2(b.cheiaAs + 1) + '. Depois disso o sol sobra e vai para a rede barato, enquanto a ponta compra caro.'
        : 'Quase todo o sol é usado na hora; a ponta depende da rede.',
      kpis: [
        { valor: R(b.exp), un: 'kWh', rotulo: 'sol exportado', cor: '#b97a08' },
        { valor: R(b.bat), un: 'kWh', rotulo: 'bateria na ponta', cor: '#0f7a51' },
        { valor: R(b.redePonta), un: 'kWh', rotulo: 'rede na ponta', cor: '#d31e2c' },
      ],
      compra: {
        ok: compra.ok, linha: compra.ok ? 'Economia de ' + compra.valor : (b.soc17 >= b.cap * 0.95 ? 'O sol já enche a bateria' : 'Ganho abaixo de R$ ' + ECON_MIN),
        pontos: compra.ok
          ? ['Comprar ' + R(pc.compra) + ' kWh entre 03h e 06h a R$ 0,85', 'Tira ' + R(b.redePonta - pc.redePonta) + ' kWh da ponta a R$ 1,50']
          : ['A energia comprada tomaria o lugar da solar' + (b.soc17 >= b.cap * 0.95 ? '' : ''),
             ...(melhor.diasCompra ? ['Passa a valer com bateria de ' + melhor.kwh + ' kWh: ' + melhor.diasCompra + ' dias nublados na semana'] : [])],
      },
      bateria: {
        ok: vale, linha: (vale ? 'Retorno em ' : 'Retorno longo: ') + anos(melhor.payback),
        melhor: opcoes.indexOf(melhor),
        opcoes: opcoes.map(o => ({ rotulo: '+' + o.extra, econ: 'R$ ' + R(o.econAno), inv: 'R$ ' + R(o.inv / 1000) + ' mil', payback: anos(o.payback),
          redePonta: R(o.hojeRedePonta), exp: R(o.hojeExp), equilibrio: 'R$ ' + R(o.econAno * 8 / o.extra) })),
        redePontaHoje: R(b.redePonta), expHoje: R(b.exp),
      },
    };
    return { leitura, compra, bateria, resumo, ui,
      premissa: 'Premissas: bateria LFP a R$ ' + R(CUSTO_BESS_KWH) + '/kWh instalado, potência 0,5C, eficiência de 95% por sentido; economia anual extrapolada da semana prevista de outubro (verão rende mais sol, inverno menos).' };
  };

  // balanço com todas as recomendações aplicadas (para mostrar o antes × depois)
  const balancoComShift = (d, cen = {}) => {
    const recs = loadShift(d, cen);
    if (!recs.length) return null;
    const opt = {};
    recs.forEach(r => {
      if (r.opt.preCarga) opt.preCarga = true;
      if (r.opt.mover) opt.mover = { ...(opt.mover || {}), ...r.opt.mover };
    });
    return { recs, opt, depois: balanco(d, cen, opt) };
  };

  const iv = (alvo) => D.intervalos[alvo];

  // perfil do dia (K-Means da Parte 3 do notebook): o centróide mais próximo dos
  // kWh previstos de galeria, eletroposto e solar, nas mesmas escalas padronizadas
  const perfilDia = (d, cen = {}) => {
    const P = D.perfis;
    if (!P || !P.centroides) return null;
    const x = [preverDia('galeria', d, cen).total, preverDia('ev', d, cen).total, solarDia(d, cen).reduce((a, b) => a + b, 0)];
    const z = x.map((v, i) => (v - P.media[i]) / P.desvio[i]);
    let melhor = 0, dist = Infinity;
    P.centroides.forEach((c, k) => {
      const dd = c.reduce((s, ci, i) => s + (ci - z[i]) ** 2, 0);
      if (dd < dist) { dist = dd; melhor = k; }
    });
    return { k: melhor, nome: P.nomes[melhor], acao: P.acoes[melhor] };
  };

  // efeito de cada fator no total do dia, por contrafactual:
  // "quanto muda a previsão se este fator estivesse no normal de outubro?"
  // No eletroposto o clima entra como um efeito só: separado, temperatura e
  // sol ficam dentro do ruído de poucas sessões por hora e se anulam.
  const virg = (v, c = 1) => (Math.round(v * 10 ** c) / 10 ** c).toString().replace('.', ',');
  const explicarDia = (alvo, d, cen = {}) => {
    const base = preverDia(alvo, d, cen).total;
    const dif = (c2) => base - preverDia(alvo, d, { ...cen, ...c2 }).total;
    const alt = (c2) => preverDia(alvo, d, { ...cen, ...c2 }).horas;   // previsão hora a hora sem o fator
    const cal = D.calendario[d];
    const cl = climaDia(d, cen);
    const tmax = Math.max(...cl.temperatura), tmaxN = Math.max(...D.normais.temperatura);
    const irrD = cl.irradiancia.reduce((a, b) => a + b, 0) / 1000;
    const irrN = D.normais.irradiancia.reduce((a, b) => a + b, 0) / 1000;
    const chuva = cl.precipitacao.slice(9, 21).reduce((a, b) => a + b, 0);
    const detTemp = 'máx ' + virg(tmax) + ' °C (típico ' + Math.round(tmaxN) + ' °C)';
    const detSol = virg(irrD) + ' kWh/m² de sol (típico ' + virg(irrN) + ')';
    const fx = [];
    if (alvo === 'ev') {
      fx.push({ k: 'clima', label: 'Clima', det: detTemp + ' · ' + (chuva > 0.4 ? virg(chuva) + ' mm de chuva' : virg(irrD) + ' kWh/m² de sol'),
        kwh: dif({ tempNormal: true, tempDelta: 0, solNormal: true, semChuva: true }), alt: alt({ tempNormal: true, tempDelta: 0, solNormal: true, semChuva: true }) });
    } else {
      fx.push({ k: 'temp', label: 'Temperatura', det: detTemp + ' · climatização', kwh: dif({ tempNormal: true, tempDelta: 0 }), alt: alt({ tempNormal: true, tempDelta: 0 }) });
      fx.push({ k: 'sol', label: 'Insolação', det: detSol + ' · carga térmica', kwh: dif({ solNormal: true }), alt: alt({ solNormal: true }) });
      if (chuva > 0.4) fx.push({ k: 'chuva', label: 'Chuva', det: virg(chuva) + ' mm no horário comercial', kwh: dif({ semChuva: true }), alt: alt({ semChuva: true }) });
    }
    if (cal.feriado || cal.vespera_feriado || cal.ponte || cal.fator_comercial !== 1) {
      const nome = [cal.nome_feriado, cal.data_comercial].filter(Boolean).join(' · ') || (cal.ponte ? 'Ponte' : 'Véspera de feriado');
      fx.push({ k: 'cal', label: cal.feriado ? 'Feriado' : 'Data especial', det: nome + (cal.feriado ? ' · abre ' + cal.abre + 'h–' + cal.fecha + 'h' : ''), kwh: dif({ semFeriado: true }), alt: alt({ semFeriado: true }) });
    }
    let soma = 0; const mediaH = new Array(24).fill(0);
    for (let k = 0; k < 7; k++) { const p = preverDia(alvo, d, { ...cen, dow: k }); soma += p.total; p.horas.forEach((x, h) => { mediaH[h] += x / 7; }); }
    fx.push({ k: 'dow', label: 'Dia da semana', det: DSEM_LONGO[cal.dia_semana] + ' vs média dos 7 dias', kwh: base - soma / 7, alt: mediaH });
    if (alvo === 'ev' && cen.vagas != null && cen.vagas < 4) {
      // vaga parada só pode tirar energia; efeito positivo seria ruído do modelo
      const fxVagas = dif({ vagas: 4 });
      if (fxVagas < 0) fx.push({ k: 'vagas', label: 'Vaga em falha', det: cen.vagas + ' de 4 vagas operando', kwh: fxVagas, alt: alt({ vagas: 4 }) });
    }
    return fx.filter(f => Math.abs(f.kwh) >= Math.max(0.5, base * (alvo === 'ev' ? 0.025 : 0.01)))
      .sort((a, b) => Math.abs(b.kwh) - Math.abs(a.kwh));
  };

  const fmtData = (iso) => { const [, m, d] = iso.split('-'); return d + '/' + m; };
  const isoLocal = (dt) => dt.getFullYear() + '-' + String(dt.getMonth() + 1).padStart(2, '0') + '-' + String(dt.getDate()).padStart(2, '0');
  const rotuloDia = (d) => {
    const cal = D.calendario[d];
    const hoje = new Date();
    const rel = cal.data === isoLocal(hoje) ? 'Hoje' : cal.data === isoLocal(new Date(hoje.getTime() + 864e5)) ? 'Amanhã' : null;
    return { curto: DSEM[cal.dia_semana], num: fmtData(cal.data).slice(0, 2), data: fmtData(cal.data), rel, longo: DSEM_LONGO[cal.dia_semana] };
  };
  const quandoDia = (d) => { const r = rotuloDia(d); return (r.rel ? r.rel + ' · ' : '') + r.longo + ' ' + r.data; };

  // ---- Síndico Virtual: lê a previsão da semana e transforma em alerta.
  // Um alerta por assunto (não um por dia), com o pior dia em destaque.
  const hh = (h) => String(h).padStart(2, '0') + 'h';
  const faixa = (hs) => (hs.length ? hh(hs[0]) + '–' + hh(hs[hs.length - 1] + 1) : '');
  const blocos = (arr) => {   // horas consecutivas, maior bloco primeiro
    const b = []; let cur = [];
    arr.forEach(h => { if (cur.length && h !== cur[cur.length - 1] + 1) { b.push(cur); cur = []; } cur.push(h); });
    if (cur.length) b.push(cur);
    return b.sort((x, z) => z.length - x.length);
  };
  const listaDias = (ds) => ds.map(d => DSEM[D.calendario[d].dia_semana].toLowerCase() + ' ' + fmtData(D.calendario[d].data).slice(0, 2)).join(', ');

  const resumoSemana = (cen = {}) => {
    let pico = null;
    for (let d = 0; d < D.calendario.length; d++) {
      redeDia(d, cen).forEach(x => { if (!pico || x.rede > pico.rede) pico = { ...x, d }; });
    }
    return { pico, pct: pico.rede / LIMITE };
  };

  const alertas = (cen = {}) => {
    const out = [];
    const vagas = cen.vagas != null ? cen.vagas : 4;
    const capEv = vagas * D.kwVaga;
    const N = D.calendario.length;
    const dem = [], cap = [], sobra = [], shifts = [];
    for (let d = 0; d < N; d++) {
      const cal = D.calendario[d];
      const rede = redeDia(d, cen);
      const pico = rede.reduce((a, b) => (b.rede > a.rede ? b : a));
      if (pico.rede > LIMITE * 0.9) dem.push({ d, pico, hs: rede.filter(x => x.rede > LIMITE * 0.9).map(x => x.h) });
      const ev = preverDia('ev', d, cen).horas;
      const cheias = ev.map((v, h) => (v >= capEv * 0.72 ? h : -1)).filter(h => h >= 0);
      if (cheias.length >= 2) cap.push({ d, b: blocos(cheias)[0], pk: Math.max(...cheias.map(h => ev[h])) });
      const ociosas = rede.filter(x => x.h >= cal.ep_abre && x.h < cal.ep_fecha && x.liq < -3 && x.ev < capEv * 0.45).map(x => x.h);
      if (ociosas.length >= 2) {
        const b = blocos(ociosas)[0];
        sobra.push({ d, b, kwh: b.reduce((a, h) => a - rede[h].liq, 0) });
      }
      const ls = loadShift(d, cen);
      if (ls.length) shifts.push({ d, recs: ls, econ: ls.reduce((x, r) => x + r.econ, 0) });
      if (cal.feriado || cal.fator_comercial >= 1.15) {
        const pe = preverDia('ev', d, cen).total, pg = preverDia('galeria', d, cen).total;
        const nome = [cal.nome_feriado, cal.data_comercial].filter(Boolean).join(' e ');
        out.push({
          id: 'ml-cal-' + d, sev: 'info', d, quando: quandoDia(d), tipo: 'cal',
          titulo: (cal.feriado ? 'Feriado: ' : 'Data comercial: ') + nome,
          resumo: 'Eletroposto aberto das ' + hh(cal.ep_abre) + ' às ' + hh(cal.ep_fecha) + '. Previsão de ' + Math.round(pe) + ' kWh nas vagas e ' + Math.round(pg) + ' kWh na galeria.',
          regra: 'Calendário de feriados de SP e datas comerciais, variável do modelo.',
          acao: cal.feriado ? 'Conferir a escala da equipe e o horário reduzido publicado no mapa.' : 'Movimento acima do normal: manter todas as vagas publicadas.',
          botao: 'Ver previsão do dia', acaoTipo: 'dia',
        });
      }
    }
    if (shifts.length) {
      const w = shifts.reduce((a, b) => (b.econ > a.econ ? b : a));
      const tot = shifts.reduce((a, x) => a + x.econ, 0);
      const tipos = {};
      shifts.forEach(x => x.recs.forEach(r => { tipos[r.tipo] = (tipos[r.tipo] || 0) + 1; }));
      const nomes = { precarga: 'carregar a bateria de madrugada', ev: 'puxar a recarga para o horário de sol', gal: 'pré-resfriar a galeria' };
      out.push({
        id: 'ml-shift', sev: tot >= 50 ? 'atencao' : 'info', d: w.d, quando: quandoDia(w.d) + (shifts.length > 1 ? ' e mais ' + (shifts.length - 1) : ''), tipo: 'shift',
        titulo: 'Load-shifting recomendado em ' + shifts.length + (shifts.length > 1 ? ' dias' : ' dia') + ': economia de R$ ' + Math.round(tot),
        resumo: 'Dias: ' + listaDias(shifts.map(x => x.d)) + '. Maior ganho ' + DSEM_LONGO[D.calendario[w.d].dia_semana] + ' (R$ ' + Math.round(w.econ) + '): ' + w.recs.map(r => r.titulo.toLowerCase()).join('; ') + '.',
        regra: 'Balanço previsto de energia (modelos de galeria e eletroposto, solar pela irradiância Open-Meteo, bateria de 30 kWh) comparado com o balanço deslocado. Ponta R$ 1,50/kWh, fora de ponta R$ 0,85/kWh. A previsão planeja e a medição do SEMS fatura (RN008).',
        acao: Object.keys(tipos).map(k => nomes[k] + (tipos[k] > 1 ? ' (' + tipos[k] + ' dias)' : '')).join(', ').replace(/^./, c => c.toUpperCase()) + '. O plano hora a hora está na Previsão de cada dia.',
        botao: 'Ver plano do dia', acaoTipo: 'dia', dias: shifts.map(x => x.d),
      });
    }
    // classificador da Parte 1 do notebook (Random Forest balanceado): horas de demanda Alta.
    // Foi calculado com as vagas da última leitura; num cenário diferente, não se aplica.
    if (D.nivelPrevisto && vagas === D.vagasNaPrevisao) {
      const altas = [];
      for (let d = 0; d < N; d++) {
        const hs = []; for (let h = 0; h < 24; h++) if (D.nivelPrevisto[d * 24 + h] === 'Alta') hs.push(h);
        if (hs.length) altas.push({ d, hs });
      }
      if (altas.length) {
        const w = altas.reduce((a, b) => (b.hs.length > a.hs.length ? b : a));
        const tot = altas.reduce((a, x) => a + x.hs.length, 0);
        out.push({
          id: 'ml-alta', sev: 'atencao', d: w.d, quando: quandoDia(w.d) + (altas.length > 1 ? ' e mais ' + (altas.length - 1) : ''), tipo: 'alta',
          titulo: 'Demanda Alta prevista em ' + tot + (tot > 1 ? ' horas' : ' hora'),
          resumo: altas.map(x => DSEM_LONGO[D.calendario[x.d].dia_semana] + ' ' + x.hs.map(hh).join(', ')).join(' · ') + '.',
          regra: 'Classificador Random Forest balanceado: pico de 15 min ≥ 35 kW na rede, 72% do teto de 48,4 kW. No teste, não deixou passar nenhuma hora Alta como Baixa.',
          acao: 'Entrar nessas horas com a bateria carregada e acompanhar o DLM; se o pico se confirmar, ele limita as vagas antes de chegar à demanda contratada.',
          botao: 'Ver previsão do dia', acaoTipo: 'dia', alvo: 'galeria',
        });
      }
    }
    if (dem.length) {
      const w = dem.reduce((a, b) => (b.pico.rede > a.pico.rede ? b : a));
      const critico = w.pico.rede > LIMITE;
      const p = w.pico;
      out.push({
        id: 'ml-dem', sev: critico ? 'critico' : 'atencao', d: w.d, quando: quandoDia(w.d) + (dem.length > 1 ? ' e mais ' + (dem.length - 1) : ''), tipo: 'dem',
        titulo: critico ? 'Risco de passar da demanda contratada' : 'Demanda perto do teto do DLM',
        resumo: 'Pico previsto de ' + virg(p.rede) + ' kW às ' + hh(p.h) + ', ' + Math.round(p.rede / LIMITE * 100) + '% do teto operacional de ' + virg(LIMITE) + ' kW. Dias: ' + listaDias(dem.map(x => x.d)) + '.',
        regra: 'Galeria ' + virg(p.gal) + ' kW + vagas ' + virg(p.ev) + ' kW − solar ' + virg(p.sol) + ' kW − bateria ' + virg(p.bess) + ' kW, acima de 90% do teto (55 kW contratados − 12% de margem).',
        acao: 'Entrar na ponta com a bateria em 100% e deixar o DLM limitar as vagas das ' + faixa(blocos(w.hs)[0]) + '. Ultrapassar a contratada gera multa na fatura do mês.',
        botao: 'Ver previsão do dia', acaoTipo: 'dia', alvo: 'galeria',
      });
    }
    if (cap.length) {
      const w = cap.reduce((a, b) => (b.b.length > a.b.length || (b.b.length === a.b.length && b.pk > a.pk) ? b : a));
      out.push({
        id: 'ml-cap', sev: 'atencao', d: w.d, quando: quandoDia(w.d) + (cap.length > 1 ? ' e mais ' + (cap.length - 1) : ''), tipo: 'cap',
        titulo: cap.length > 1 ? 'Vagas lotadas em ' + cap.length + ' dos ' + N + ' dias' : 'Vagas lotadas ' + DSEM_LONGO[D.calendario[w.d].dia_semana] + ' ' + faixa(w.b),
        resumo: 'Pior momento: ' + DSEM_LONGO[D.calendario[w.d].dia_semana] + ' ' + faixa(w.b) + ', até ' + virg(w.pk) + ' kWh/h para ' + capEv + ' kW de capacidade'
          + (vagas < 4 ? ' com ' + vagas + ' vagas operando' : '') + '. Dias: ' + listaDias(cap.map(x => x.d)) + '.',
        regra: 'Previsão ML do eletroposto acima de 72% da capacidade das vagas por 2 horas seguidas ou mais. Acima disso, quem chega encontra as vagas ocupadas.',
        acao: vagas < 4
          ? 'Reiniciar a Vaga 03: com as 4 vagas a capacidade sobe de ' + capEv + ' para 28 kW. Se não voltar, abrir chamado ainda hoje.'
          : 'Subir a tarifa base em 5% a 8% nessas faixas para espalhar a procura ao longo do dia.',
        botao: vagas < 4 ? 'Abrir Vagas e falhas' : 'Ver Tarifa', acaoTipo: vagas < 4 ? 'vagas' : 'tarifa', alvo: 'ev',
      });
    }
    // excedente com vagas ociosas: se o load-shifting já propõe puxar a recarga para o sol, não repete
    if (sobra.length && !shifts.some(x => x.recs.some(r => r.tipo === 'ev'))) {
      const tot = sobra.reduce((a, x) => a + x.kwh, 0);
      const w = sobra.reduce((a, b) => (b.kwh > a.kwh ? b : a));
      out.push({
        id: 'ml-exc', sev: 'info', d: w.d, quando: quandoDia(w.d) + (sobra.length > 1 ? ' e mais ' + (sobra.length - 1) : ''), tipo: 'exc',
        titulo: 'Sol sobrando com vagas ociosas',
        resumo: 'Cerca de ' + Math.round(tot) + ' kWh de excedente solar devem ir para a rede na semana com as vagas abaixo de 45% de uso. Maior sobra: ' + DSEM_LONGO[D.calendario[w.d].dia_semana] + ' ' + faixa(w.b) + '.',
        regra: 'Geração solar prevista acima do consumo da galeria e das vagas, com o eletroposto aberto.',
        acao: 'Manter o fator α de solar alto (−12%) nessas faixas para atrair recargas: vender o excedente na vaga rende mais que exportar.',
        botao: 'Ver Tarifa', acaoTipo: 'tarifa', alvo: 'ev',
      });
    }
    const peso = { critico: 0, atencao: 1, info: 2 };
    return out.sort((a, b) => peso[a.sev] - peso[b.sev] || a.d - b.d);
  };

  return {
    nivelHoras: (d) => { const n = { Alta: 0, 'Média': 0, Baixa: 0 }; if (D.nivelPrevisto) for (let h = 0; h < 24; h++) n[D.nivelPrevisto[d * 24 + h]]++; return n; },
    _avaliar: avaliar, D, DSEM, DSEM_LONGO, LIMITE, PONTA, TARIFA, preverDia, solarDia, redeDia, balanco, loadShift, balancoComShift, analiseDia, explicarDia, alertas, resumoSemana, rotuloDia, quandoDia, iv, virg, perfilDia,
    dias: () => D.calendario.length,
  };
})();
