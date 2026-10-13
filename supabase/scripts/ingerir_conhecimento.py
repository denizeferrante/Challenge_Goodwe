"""
Carrega a base de conhecimento do assistente no Supabase (pgvector).

Mesma lógica de fontes do src/rag.py da Sprint 03 (PDFs, DOCX e FAQ), mas em vez
de um InMemoryVectorStore que some a cada execução, grava os trechos e os
embeddings na tabela ia_conhecimento (migration 20261012000000_assistente_ia.sql).

    pip install openai pypdf docx2txt requests python-dotenv
    export OPENAI_API_KEY=... SUPABASE_URL=https://<projeto>.supabase.co SUPABASE_SERVICE_ROLE_KEY=...
    python supabase/scripts/ingerir_conhecimento.py            # adiciona
    python supabase/scripts/ingerir_conhecimento.py --limpar   # apaga e recarrega
"""
import glob
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
BASE = Path(__file__).resolve().parent.parent / "conhecimento"
URL = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/ia_conhecimento"
HEAD = {
    "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "Content-Type": "application/json",
}
MODELO_EMB = os.getenv("GOODWE_EMBEDDING_MODEL", "text-embedding-3-small")
TAM, SOBRE = 1000, 200  # mesmo chunk_size/overlap da Sprint 03


def dividir(texto: str) -> list[str]:
    texto = re.sub(r"\s+", " ", texto).strip()
    out, i = [], 0
    while i < len(texto):
        out.append(texto[i:i + TAM])
        i += TAM - SOBRE
    return [t for t in out if len(t) > 40]


def faq() -> list[dict]:
    trechos = []
    md = (BASE / "faq_app.md").read_text(encoding="utf-8")
    for bloco in re.split(r"^## ", md, flags=re.M)[1:]:
        titulo, _, corpo = bloco.partition("\n")
        m = re.match(r"publico:\s*(\w+)\s*\n", corpo)
        publico = m.group(1) if m else "todos"
        corpo = corpo[m.end():] if m else corpo
        trechos.append({"fonte": "faq", "titulo": titulo.strip(), "conteudo": corpo.strip(), "publico": publico})
    return trechos


def documentos() -> list[dict]:
    trechos = []
    for caminho in glob.glob(str(BASE / "**" / "*.pdf"), recursive=True):
        from pypdf import PdfReader
        texto = "\n".join(p.extract_text() or "" for p in PdfReader(caminho).pages)
        trechos += [{"fonte": "pdf", "titulo": Path(caminho).stem, "conteudo": t, "publico": "todos"} for t in dividir(texto)]
    for caminho in glob.glob(str(BASE / "**" / "*.docx"), recursive=True):
        import docx2txt
        trechos += [{"fonte": "docx", "titulo": Path(caminho).stem, "conteudo": t, "publico": "todos"} for t in dividir(docx2txt.process(caminho))]
    return trechos


def main():
    if "--limpar" in sys.argv:
        requests.delete(URL + "?id=gt.0", headers=HEAD, timeout=30).raise_for_status()
    trechos = faq() + documentos()
    cli = OpenAI()
    for i in range(0, len(trechos), 64):
        lote = trechos[i:i + 64]
        embs = cli.embeddings.create(model=MODELO_EMB, input=[t["titulo"] + "\n" + t["conteudo"] for t in lote]).data
        linhas = [{**t, "embedding": e.embedding} for t, e in zip(lote, embs)]
        requests.post(URL, headers=HEAD, json=linhas, timeout=60).raise_for_status()
        print(f"[ingestão] {i + len(lote)}/{len(trechos)} trechos")
    print("[ingestão] concluída")


if __name__ == "__main__":
    main()
