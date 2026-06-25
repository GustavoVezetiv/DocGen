"""
main.py - Backend do DocGen
Servidor FastAPI que recebe HTML + CSS e gera PDF com WeasyPrint
"""
import io
import asyncio
import logging

import bleach
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import weasyprint

# -------------------------------------------------------------------
# Configuração básica de logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docgen")

# -------------------------------------------------------------------
# CSS global que simula um padrão executivo / profissional
# -------------------------------------------------------------------
CSS_GLOBAL = """
@page {
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9pt;
        color: #888;
    }
}

*, *::before, *::after {
    box-sizing: border-box;
}

html {
    font-size: 11pt;
    color: #1a1a1a;
}

body {
    font-family: "Georgia", "Times New Roman", serif;
    line-height: 1.7;
    margin: 0;
    padding: 0;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    color: #111;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    line-height: 1.25;
}

h1 { font-size: 22pt; border-bottom: 2px solid #2563eb; padding-bottom: 6px; }
h2 { font-size: 16pt; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
h3 { font-size: 13pt; }

p  { margin: 0.6em 0; }

a  { color: #2563eb; text-decoration: none; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
}
th {
    background: #2563eb;
    color: #fff;
    padding: 8px 12px;
    text-align: left;
}
td {
    padding: 7px 12px;
    border-bottom: 1px solid #e5e7eb;
}
tr:nth-child(even) td { background: #f8fafc; }

blockquote {
    border-left: 4px solid #2563eb;
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #eff6ff;
    color: #374151;
    font-style: italic;
}

code, pre {
    font-family: "Courier New", Courier, monospace;
    font-size: 9.5pt;
    background: #f3f4f6;
    border-radius: 3px;
}
code { padding: 1px 5px; }
pre  { padding: 12px 16px; overflow: auto; border: 1px solid #e5e7eb; }

ul, ol { padding-left: 1.5em; }
li     { margin: 0.3em 0; }

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1.5em 0;
}
"""

# -------------------------------------------------------------------
# Tags e atributos HTML permitidos pelo Bleach (sanitização)
# -------------------------------------------------------------------
ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "div", "span", "section", "article", "header", "footer", "main",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "ul", "ol", "li", "dl", "dt", "dd",
    "pre", "code", "blockquote",
    "img", "figure", "figcaption",
    "strong", "em", "u", "s", "del", "ins",
    "sup", "sub", "mark",
]

ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "*": ["class", "id", "style"],
    "img": ["src", "alt", "width", "height"],
    "a": ["href", "title"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
}

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="DocGen API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Schema da requisição
# -------------------------------------------------------------------
class DocumentRequest(BaseModel):
    html: str
    css: str = ""

# -------------------------------------------------------------------
# url_fetcher bloqueado por segurança (impede acesso a recursos externos)
# -------------------------------------------------------------------
def blocked_url_fetcher(url: str, timeout=None):
    logger.warning("Tentativa de busca de URL bloqueada: %s", url)
    raise PermissionError(f"Acesso a recursos externos bloqueado: {url}")

# -------------------------------------------------------------------
# Geração de PDF (executada em thread separada)
# -------------------------------------------------------------------
def _render_pdf(full_html: str) -> bytes:
    """Renderiza o HTML em PDF usando WeasyPrint."""
    pdf_buffer = io.BytesIO()
    weasyprint.HTML(string=full_html).write_pdf(
        pdf_buffer,
        url_fetcher=blocked_url_fetcher,
    )
    return pdf_buffer.getvalue()

# -------------------------------------------------------------------
# Endpoint principal
# -------------------------------------------------------------------
@app.post("/generate-pdf")
async def generate_pdf(request: DocumentRequest):
    """
    Recebe HTML + CSS do usuário, sanitiza, compila com WeasyPrint
    e retorna o PDF como download.
    """
    # 1. Sanitiza o HTML para remover scripts maliciosos
    clean_html = bleach.clean(
        request.html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )

    # 2. Monta o documento completo: CSS global + CSS local + HTML do usuário
    full_html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <style>{CSS_GLOBAL}</style>
    <style>{request.css}</style>
</head>
<body>
{clean_html}
</body>
</html>"""

    logger.info("Gerando PDF — tamanho do HTML: %d bytes", len(full_html))

    try:
        # 3. Executa o WeasyPrint em thread separada para não bloquear o loop assíncrono
        pdf_bytes = await asyncio.to_thread(_render_pdf, full_html)
    except Exception as exc:
        logger.exception("Erro ao gerar PDF")
        raise HTTPException(status_code=500, detail=f"Erro na geração do PDF: {exc}")

    # 4. Retorna o PDF binário como streaming response
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=documento.pdf"},
    )

@app.get("/health")
async def health():
    return {"status": "ok"}
