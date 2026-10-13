#!/usr/bin/env python3
"""
Monta o app ChargeGrid a partir dos fontes em src/.

    python3 build.py

Gera dois arquivos, ambos versionados no repositorio:

  index.html                -> versao multi-arquivo. Carrega src/styles/*.css,
                               vendor/*.js e assets/* por caminho relativo.
                               E a versao para desenvolver e para o GitHub Pages.

  dist/ChargeGrid-app.html  -> versao de arquivo unico. CSS, JS, fontes e
                               imagens embutidos (fontes e imagens como data:
                               URI). Abre com dois cliques, sem servidor, e e
                               o arquivo para enviar por e-mail ou pendrive.

E, se o .env da raiz tiver SUPABASE_ANON_KEY, gera tambem (fora do Git):

  dist/ChargeGrid-app-local.html -> igual ao anterior, mas com a chave anon no
                               lugar de '<anon-key>', para o assistente IA e os
                               pagamentos chamarem o Supabase de verdade. A chave
                               fica so no .env; o repositorio nunca a recebe.

Por que existe um build: o runtime do Claude Design (vendor/dc-runtime.js) le a
logica do componente pelo textContent da tag <script data-dc-script>, ou seja,
ela precisa estar embutida no HTML -- nao da para carregar src/app.js por src="".
O build resolve isso costurando os pedacos. Edite sempre src/, nunca os gerados.
"""

import base64
import json
import mimetypes
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))


def ler(*partes):
    with open(os.path.join(BASE, *partes), encoding="utf-8") as f:
        return f.read()


def ler_bytes(caminho_rel):
    with open(os.path.join(BASE, caminho_rel), "rb") as f:
        return f.read()


def data_uri(caminho_rel):
    mime = mimetypes.guess_type(caminho_rel)[0] or "application/octet-stream"
    if caminho_rel.endswith(".woff2"):
        mime = "font/woff2"
    b64 = base64.b64encode(ler_bytes(caminho_rel)).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


template = ler("src", "template.html").strip()
# A previsão de demanda (machine learning) entra antes da lógica do app:
#   src/ml/previsao-dados.js  -> GERADO pelo notebook ../inteligencia/ChargeGrid_ML.ipynb (exportar_app.py)
#   src/ml/previsao-motor.js  -> roda as árvores do modelo no navegador
#   src/pagamento/gateway.js  -> cliente da API de pagamento (sandbox ou Edge Function)
# O runtime avalia tudo num único new Function, então as constantes ML_DADOS e
# MLPrev ficam visíveis para a class Component, como BRL e HW_URLS já ficavam.
ML_JS = ["previsao-dados.js", "previsao-motor.js"]
app_js = ("".join(ler("src", "ml", n).rstrip() + "\n\n" for n in ML_JS)
          + ler("src", "pagamento", "gateway.js").rstrip() + "\n\n"
          + ler("src", "ia", "snapshot.js").rstrip() + "\n\n"
          + ler("src", "ia", "assistente.js").rstrip() + "\n\n"
          + ler("src", "app.js").rstrip())
fonts_css = ler("src", "styles", "fonts.css").strip()
app_css = ler("src", "styles", "app.css").strip()
props = json.loads(ler("src", "props.json"))

props_attr = (
    json.dumps(props, ensure_ascii=False, separators=(",", ":"))
    .replace("&", "&amp;")
    .replace('"', "&quot;")
    .replace("<", "&lt;")
)

VENDOR = [
    "vendor/react.production.min.js",
    "vendor/react-dom.production.min.js",
    "vendor/dc-runtime.js",
]

CABECALHO = (
    "<!DOCTYPE html>\n"
    "<html lang=\"pt-BR\">\n"
    "<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "<title>ChargeGrid - Prototipo navegavel</title>\n"
    "<!-- GERADO POR build.py - nao edite este arquivo, edite src/ -->\n"
)


def montar(vendor_tags, style_tags, ancora_assets=lambda t: t):
    return (
        CABECALHO
        + vendor_tags
        + "</head>\n<body>\n<x-dc>\n<helmet data-dc-atomics=\"\">\n"
        + style_tags
        + "\n</helmet>\n"
        + ancora_assets(template)
        + "\n</x-dc>\n"
        + '<script type="text/x-dc" data-dc-script="" data-props="'
        + props_attr
        + '">\n'
        + app_js
        + "\n</script>\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------- multi-arquivo
multi = montar(
    vendor_tags="".join('<script src="%s"></script>\n' % v for v in VENDOR),
    style_tags='<link rel="stylesheet" href="src/styles/fonts.css">\n'
    '<link rel="stylesheet" href="src/styles/app.css">',
)
with open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
    f.write(multi)

# -------------------------------------------------------------- arquivo unico
def inline_urls_css(css):
    """Troca url("../../assets/...") por data: URI, para a versao de arquivo unico."""
    return re.sub(
        r'url\("\.\./\.\./assets/([^"]+)"\)',
        lambda m: 'url("%s")' % data_uri("assets/" + m.group(1)),
        css,
    )


fonts_inline = inline_urls_css(fonts_css)
app_css_inline = inline_urls_css(app_css)

# caminho sempre com "/" (no Windows os.path.join usaria "\\" e o template não casaria)
IMAGENS = sorted(
    "assets/img/" + n for n in os.listdir(os.path.join(BASE, "assets", "img"))
)

def embutir_imagens(texto):
    for caminho in IMAGENS:
        texto = texto.replace(caminho, data_uri(caminho))
    return texto


unico = montar(
    vendor_tags="".join(
        "<script>\n%s\n</script>\n" % ler_bytes(v).decode("utf-8") for v in VENDOR
    ),
    style_tags="<style>\n%s\n</style>\n<style>\n%s\n</style>"
    % (fonts_inline, app_css_inline),
    ancora_assets=embutir_imagens,
)
os.makedirs(os.path.join(BASE, "dist"), exist_ok=True)
with open(os.path.join(BASE, "dist", "ChargeGrid-app.html"), "w", encoding="utf-8") as f:
    f.write(unico)

print("index.html               %8.1f KB" % (len(multi.encode()) / 1024))
print("dist/ChargeGrid-app.html %8.1f KB" % (len(unico.encode()) / 1024))


def chave_anon():
    """Le SUPABASE_ANON_KEY do .env da raiz do projeto (sem depender de pacotes)."""
    env = os.path.join(BASE, "..", ".env")
    if not os.path.exists(env):
        return ""
    for linha in open(env, encoding="utf-8-sig"):
        nome, _, valor = linha.strip().partition("=")
        if nome.strip() == "SUPABASE_ANON_KEY":
            return valor.strip().strip("'\"")
    return ""


anon = chave_anon()
if anon:
    local = unico.replace("IA_ANON_KEY = '<anon-key>'", "IA_ANON_KEY = '%s'" % anon)
    with open(os.path.join(BASE, "dist", "ChargeGrid-app-local.html"), "w", encoding="utf-8") as f:
        f.write(local)
    print("dist/ChargeGrid-app-local.html (com a chave anon do .env, fora do Git)")
else:
    print("sem SUPABASE_ANON_KEY no .env: IA e pagamentos reais so funcionam com ela")
