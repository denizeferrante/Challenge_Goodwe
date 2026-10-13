#!/usr/bin/env python3
"""
Confere que o motor JS do app (app/src/ml/previsao-motor.js) reproduz o
scikit-learn: (1) mesma saída do Random Forest para 400 linhas sorteadas;
(2) mesmas variáveis e mesma previsão para as 168 horas da semana prevista.

    python3 testar_paridade_js.py      (requer node; rode depois do notebook)
"""
import json, os, subprocess, sys, tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
ML = os.path.join(BASE, "..", "app", "src", "ml")
js = open(os.path.join(ML, "previsao-dados.js"), encoding="utf-8").read() + "\n" + \
     open(os.path.join(ML, "previsao-motor.js"), encoding="utf-8").read() + """
const REF = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const alvo of Object.keys(REF)) {
  const m = MLPrev.D.modelos[alvo];
  let maxArv = 0, maxSem = 0;
  REF[alvo].X.forEach((x0, i) => {
    const x = x0.map(v => (v === null ? NaN : v));
    maxArv = Math.max(maxArv, Math.abs(MLPrev._avaliar(m, x) - REF[alvo].y[i]));
  });
  for (let d = 0; d < 7; d++) {
    MLPrev.preverDia(alvo, d, { vagas: 3 }).horas.forEach((v, h) => {
      maxSem = Math.max(maxSem, Math.abs(v - REF[alvo].futuro[d * 24 + h]));
    });
  }
  out[alvo] = { maxErroArvores: maxArv, maxErroSemana: maxSem };
}
console.log(JSON.stringify(out));
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
    f.write(js)
res = json.loads(subprocess.check_output(["node", f.name, os.path.join(BASE, "resultados", "paridade_js.json")]))
# folhas exportadas com 6 casas decimais: diferença residual de ~1e-6 kWh.
# Um caminho errado numa árvore daria erro de ordem 0,01 kWh ou mais.
ok = all(v["maxErroArvores"] < 1e-3 and v["maxErroSemana"] < 1e-3 for v in res.values())
print(json.dumps(res, indent=2))
print("PARIDADE OK" if ok else "DIVERGÊNCIA ENTRE PYTHON E JS")
sys.exit(0 if ok else 1)
