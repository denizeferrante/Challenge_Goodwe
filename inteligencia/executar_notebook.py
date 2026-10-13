#!/usr/bin/env python3
"""
Executa um .ipynb célula a célula e grava as saídas (texto, tabelas e
gráficos) dentro do próprio arquivo — o equivalente a "Reiniciar e executar
tudo" do Jupyter/Colab, sem precisar do Jupyter instalado.

    python3 executar_notebook.py ChargeGrid_ML.ipynb

Linhas mágicas (%pip, !comando) são puladas: servem para o Colab.
"""
import ast
import base64
import contextlib
import io
import json
import os
import sys
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def executar(caminho):
    nb = json.load(open(caminho, encoding="utf-8"))
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.chdir(pasta)
    sys.path.insert(0, pasta)
    ns = {"__name__": "__main__"}
    contador = 0
    for cel in nb["cells"]:
        if cel["cell_type"] != "code":
            continue
        contador += 1
        saidas = []

        def figura():
            for num in plt.get_fignums():
                buf = io.BytesIO()
                plt.figure(num).savefig(buf, format="png", dpi=90, bbox_inches="tight")
                saidas.append({"output_type": "display_data", "metadata": {},
                               "data": {"image/png": base64.b64encode(buf.getvalue()).decode(),
                                        "text/plain": ["<Figure>"]}})
            plt.close("all")

        def mostrar(obj):
            dados = {"text/plain": [repr(obj)]}
            if hasattr(obj, "_repr_html_"):
                html = obj._repr_html_()
                if html:
                    dados["text/html"] = [html]
            saidas.append({"output_type": "display_data", "metadata": {}, "data": dados})

        ns["display"] = mostrar
        plt.show = figura
        fonte = "".join(cel["source"])
        codigo = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith(("%", "!")))
        out = io.StringIO()
        try:
            arvore = ast.parse(codigo)
            ultimo = None
            if arvore.body and isinstance(arvore.body[-1], ast.Expr):
                ultimo = ast.Expression(arvore.body.pop().value)
            with contextlib.redirect_stdout(out):
                exec(compile(arvore, "<célula %d>" % contador, "exec"), ns)
                valor = eval(compile(ultimo, "<célula %d>" % contador, "eval"), ns) if ultimo else None
            if out.getvalue():
                saidas.insert(0, {"output_type": "stream", "name": "stdout", "text": out.getvalue().splitlines(True)})
            figura()
            if valor is not None:
                dados = {"text/plain": [repr(valor)]}
                if hasattr(valor, "_repr_html_"):
                    html = valor._repr_html_()
                    if html:
                        dados["text/html"] = [html]
                saidas.append({"output_type": "execute_result", "execution_count": contador, "metadata": {}, "data": dados})
        except Exception as e:  # registra o erro na célula, como o Jupyter
            if out.getvalue():
                saidas.insert(0, {"output_type": "stream", "name": "stdout", "text": out.getvalue().splitlines(True)})
            saidas.append({"output_type": "error", "ename": type(e).__name__, "evalue": str(e),
                           "traceback": traceback.format_exc().splitlines()})
            cel["outputs"], cel["execution_count"] = saidas, contador
            json.dump(nb, open(caminho, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("ERRO na célula", contador, "\n", traceback.format_exc())
            sys.exit(1)
        cel["outputs"], cel["execution_count"] = saidas, contador
        print("célula", contador, "ok")
    json.dump(nb, open(caminho, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    executar(sys.argv[1])
