"""
Confere se o .env está certo, sem mostrar as chaves na tela.

    pip install requests python-dotenv
    python supabase/scripts/testar_env.py

Testa: o arquivo existe com o nome certo, as 3 variáveis estão preenchidas,
a chave da OpenAI é aceita e a URL + service_role do Supabase respondem.
"""
import base64
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
ok_geral = True


def linha(ok: bool, texto: str):
    global ok_geral
    ok_geral &= ok
    print(("  OK   " if ok else "  ERRO ") + texto)


print("\n1. Arquivo .env")
env = RAIZ / ".env"
if not env.exists():
    extra = " (achei um .env.txt: renomeie para .env)" if (RAIZ / ".env.txt").exists() else ""
    linha(False, f"não existe {env}{extra}")
    sys.exit(1)
linha(True, f"encontrado em {env}")
load_dotenv(env, override=True)

print("\n2. Variáveis preenchidas")
for nome in ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
    v = os.getenv(nome, "").strip()
    vazio = not v or v.endswith("...") or "cole-aqui" in v
    linha(not vazio, f"{nome} {'preenchida' if not vazio else 'vazia ou ainda com o texto do modelo'}")
    if v != os.getenv(nome, ""):
        linha(False, f"{nome} tem espaço no começo ou no fim")

oa = os.getenv("OPENAI_API_KEY", "").strip()
url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
sr = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

print("\n3. OpenAI")
try:
    r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {oa}"}, timeout=20)
    if r.status_code == 200:
        ids = {m["id"] for m in r.json().get("data", [])}
        linha(True, "chave aceita")
        for m in ["gpt-4o-mini", "text-embedding-3-small"]:
            linha(m in ids, f"modelo {m} {'disponível' if m in ids else 'não aparece para esta chave'}")
    else:
        linha(False, f"a OpenAI recusou a chave (HTTP {r.status_code}): {r.json().get('error', {}).get('message', '')[:120]}")
except Exception as e:
    linha(False, f"não consegui falar com a OpenAI: {e}")

print("\n4. Supabase")
if not url.startswith("https://") or not url.endswith(".supabase.co"):
    linha(False, "SUPABASE_URL deve ser https://<ref>.supabase.co (sem /rest/v1 no fim)")
try:
    papel = json.loads(base64.urlsafe_b64decode(sr.split(".")[1] + "==")).get("role")
    linha(papel == "service_role", f"a chave é do tipo '{papel}'" + ("" if papel == "service_role" else " (precisa ser a service_role, não a anon)"))
except Exception:
    linha(False, "SUPABASE_SERVICE_ROLE_KEY não parece uma chave legacy (deve começar com eyJ)")
try:
    r = requests.get(url + "/rest/v1/", headers={"apikey": sr, "Authorization": f"Bearer {sr}"}, timeout=20)
    linha(r.status_code == 200, "URL e chave aceitas pelo Supabase" if r.status_code == 200 else f"Supabase respondeu HTTP {r.status_code}")
    r = requests.get(url + "/rest/v1/ia_conhecimento?select=id&limit=1", headers={"apikey": sr, "Authorization": f"Bearer {sr}"}, timeout=20)
    if r.status_code == 200:
        linha(True, "tabela ia_conhecimento existe (migration aplicada)")
    else:
        print("  --   tabela ia_conhecimento ainda não existe: rode 'npx supabase db push' (passo 4)")
except Exception as e:
    linha(False, f"não consegui falar com o Supabase: {e}")

print("\n" + ("Tudo certo com o .env." if ok_geral else "Corrija os itens com ERRO e rode de novo.") + "\n")
sys.exit(0 if ok_geral else 1)
