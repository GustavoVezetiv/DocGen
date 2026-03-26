"""
DocGen - Plataforma de Geração de PDFs de Alta Fidelidade
Fase 1: Motor Stateless com FastAPI + WeasyPrint

Arquitetura:
- API assíncrona (FastAPI)
- Processamento de PDF em thread separada (não-bloqueante)
- URL Fetcher bloqueado (SSRF Prevention)
- HTML sanitizado (XSS Prevention)
- Renderização: CSS Global → CSS Local → HTML (Cascade)
"""

import asyncio
import io
import json
import logging
from typing import Optional
from urllib.parse import urlparse

from bleach import clean as bleach_clean
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from weasyprint import HTML, CSS
from weasyprint.css.targets import TargetCollector

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES E CONFIGURAÇÃO
# ============================================================================

# Limite de payload: ~1MB
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB em bytes

# CSS Global (Design System) - Definido no backend, não editável pelo usuário
# Exemplo: ABNT, layouts corporativos, fontes padrão, cores do brand, etc.
CSS_GLOBAL = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12pt;
    color: #333;
    line-height: 1.5;
    background-color: #fff;
}

h1, h2, h3, h4, h5, h6 {
    margin-bottom: 0.5em;
    margin-top: 0.5em;
    font-weight: 600;
}

h1 {
    font-size: 24pt;
}

h2 {
    font-size: 18pt;
}

h3 {
    font-size: 14pt;
}

p {
    margin-bottom: 0.5em;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

code {
    background-color: #f4f4f4;
    padding: 2px 4px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

table th,
table td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

table th {
    background-color: #f4f4f4;
    font-weight: bold;
}

@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: "Página " counter(page) " de " counter(pages);
        font-size: 10pt;
        color: #666;
    }
}
"""

# Tags HTML permitidas após sanitização (whitelist)
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "strike",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "a",
    "img",
    "span",
    "div",
    "hr",
    "section",
    "article",
    "header",
    "footer",
    "nav",
]

# Atributos permitidos por tag
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "width", "height"],
    "div": ["class", "id"],
    "span": ["class", "id"],
    "table": ["class", "id"],
    "tr": ["class", "id"],
    "td": ["class", "id", "colspan", "rowspan"],
    "th": ["class", "id", "colspan", "rowspan"],
}

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================


class GeneratePDFRequest(BaseModel):
    """Request body para o endpoint de geração de PDF."""

    html: str = Field(
        ...,
        description="HTML do documento (obrigatório)",
        min_length=1,
        max_length=1_000_000,
    )
    css: Optional[str] = Field(
        default="",
        description="CSS customizado (opcional)",
        max_length=100_000,
    )

    @validator("html", "css", pre=True)
    def validate_string_not_empty_after_strip(cls, v):
        """Valida que as strings não são apenas espaço em branco."""
        if isinstance(v, str):
            return v.strip()
        return v


# ============================================================================
# FUNÇÕES DE SEGURANÇA
# ============================================================================


def custom_url_fetcher(url: str):
    """
    URL Fetcher customizado para WeasyPrint que bloqueia requisições externas
    e acesso a arquivos locais (SSRF Prevention).

    Args:
        url (str): URL a ser fetched

    Raises:
        ValueError: Se a URL for externa ou usar file:// protocol
    """
    parsed_url = urlparse(url)

    # Bloquear file:// protocol (acesso a arquivos locais)
    if parsed_url.scheme == "file":
        logger.warning(f"Tentativa de acesso bloqueada: file:// protocol - {url}")
        raise ValueError("Acesso a arquivos locais (file://) não é permitido")

    # Bloquear URLs externas (http, https, ftp, etc.)
    if parsed_url.scheme in ("http", "https", "ftp", "ftps"):
        logger.warning(f"Tentativa de requisição externa bloqueada: {url}")
        raise ValueError(
            "Requisições externas não são permitidas. "
            "Use URLs de dados (data:) ou imagens inline para recursos."
        )

    # schemas de dados são permitidos (data:image/..., etc.)
    if parsed_url.scheme == "data":
        # WeasyPrint pode processar data URLs nativamente
        return {
            "string": url,
            "mime_type": "image/png",
        }

    # Cualquier otro esquema es bloqueado
    logger.warning(f"Tentativa de acesso bloqueado: esquema não permitido - {url}")
    raise ValueError(f"Esquema de URL não permitido: {parsed_url.scheme}")


def sanitize_html(html: str) -> str:
    """
    Sanitiza HTML de entrada removendo tags e atributos perigosos (XSS Prevention).

    Args:
        html (str): HTML bruto do usuário

    Returns:
        str: HTML sanitizado

    Segurança:
        - Remove <script>, <iframe>, <object> e tags perigosas
        - Remove atributos on* (onclick, onload, etc.)
        - Remove javascript: URLs
    """
    sanitized = bleach_clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True,
    )
    logger.debug("HTML sanitizado com sucesso")
    return sanitized


# ============================================================================
# FUNÇÃO DE GERAÇÃO DE PDF (CPU-BOUND, EXECUTA EM THREAD SEPARADA)
# ============================================================================


def _generate_pdf_sync(html: str, css_global: str, css_user: str) -> bytes:
    """
    Função síncrona que gera o PDF. Executa em thread separada para não
    bloquear o Event Loop do FastAPI.

    Args:
        html (str): HTML sanitizado e final
        css_global (str): CSS global (design system)
        css_user (str): CSS do usuário

    Returns:
        bytes: PDF em formato binário

    Raises:
        RuntimeError: Se WeasyPrint falhar na renderização
    """
    try:
        # Construir HTML final com injeção de CSS conforme regra de renderização:
        # <style>{CSS_GLOBAL}</style>
        # <style>{CSS_LOCAL}</style>
        # {HTML_USER}
        final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documento</title>
    <style>
{css_global}
    </style>
    <style>
{css_user}
    </style>
</head>
<body>
{html}
</body>
</html>
"""

        logger.debug("Iniciando renderização de PDF com WeasyPrint")

        # Renderizar HTML com CSS injetado
        # url_fetcher customizado bloqueia SSRF
        document = HTML(
            string=final_html,
            url_fetcher=custom_url_fetcher,
        )

        # Gerar PDF em memória (BytesIO)
        pdf_bytes = io.BytesIO()
        document.write_pdf(pdf_bytes)
        pdf_bytes.seek(0)

        logger.info("PDF gerado com sucesso em memória")
        return pdf_bytes.getvalue()

    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}", exc_info=True)
        raise RuntimeError(f"Falha na renderização do PDF: {str(e)}") from e


async def generate_pdf_async(html: str, css_user: str) -> bytes:
    """
    Wrapper assíncrono que executa _generate_pdf_sync em thread separada
    usando asyncio.to_thread() para não bloquear o Event Loop.

    Args:
        html (str): HTML sanitizado
        css_user (str): CSS do usuário

    Returns:
        bytes: PDF em formato binário

    Raises:
        RuntimeError: Se a geração falhar
    """
    loop = asyncio.get_event_loop()
    try:
        pdf_bytes = await asyncio.to_thread(
            _generate_pdf_sync,
            html,
            CSS_GLOBAL,
            css_user,
        )
        return pdf_bytes
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na geração assíncrona de PDF: {str(e)}")
        raise RuntimeError(f"Erro interno na geração de PDF") from e


# ============================================================================
# APLICAÇÃO FASTAPI
# ============================================================================

app = FastAPI(
    title="DocGen API",
    description="Plataforma de Geração de PDFs de Alta Fidelidade",
    version="1.0.0",
)

# ============================================================================
# MIDDLEWARE CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Desenvolvimento local: permitir todas as origens
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MIDDLEWARE DE TAMANHO DE PAYLOAD
# ============================================================================


@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    """
    Middleware que limita o tamanho total do payload a MAX_PAYLOAD_SIZE.

    Retorna 413 Payload Too Large se o limite for excedido.
    """
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
            logger.warning(
                f"Payload rejeitado por tamanho: {content_length} bytes "
                f"(máximo: {MAX_PAYLOAD_SIZE})"
            )
            return StreamingResponse(
                io.BytesIO(
                    json.dumps(
                        {
                            "error": f"Payload muito grande. Máximo: {MAX_PAYLOAD_SIZE / 1024 / 1024}MB"
                        }
                    ).encode()
                ),
                status_code=413,
                media_type="application/json",
            )
    return await call_next(request)


# ============================================================================
# HEALTH CHECK (LIVENESS)
# ============================================================================


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Endpoint de health check para verificar se o serviço está rodando.

    Returns:
        dict: Status do serviço
    """
    return {
        "status": "healthy",
        "service": "DocGen API",
        "version": "1.0.0",
    }


# ============================================================================
# ENDPOINT PRINCIPAL: GENERATE PDF
# ============================================================================


@app.post(
    "/generate-pdf",
    summary="Gerar PDF de Alta Fidelidade",
    description="Processa HTML + CSS e retorna um PDF renderizado",
    tags=["PDF Generation"],
    responses={
        200: {"description": "PDF gerado com sucesso", "content": {"application/pdf": {}}},
        400: {"description": "Erro na requisição (JSON inválido, campos ausentes)"},
        422: {"description": "Entidade não processável (validação Pydantic falhou)"},
        500: {"description": "Erro interno na geração do PDF"},
    },
)
async def generate_pdf(request: GeneratePDFRequest):
    """
    Endpoint principal para geração de PDF.

    Fluxo:
    1. Valida request com Pydantic
    2. Sanitiza HTML (XSS Prevention)
    3. Executa geração de PDF em thread separada (non-blocking)
    4. Retorna PDF binário com headers apropriados

    Args:
        request (GeneratePDFRequest): Request body com html e css

    Returns:
        StreamingResponse: PDF binário com Content-Type application/pdf

    Raises:
        HTTPException: 400, 422 ou 500 conforme apropriado
    """
    try:
        logger.info(
            f"Requisição recebida: HTML length={len(request.html)}, "
            f"CSS length={len(request.css)}"
        )

        # Sanitizar HTML (XSS Prevention)
        html_sanitized = sanitize_html(request.html)

        if not html_sanitized.strip():
            logger.warning("HTML sanitizado resultou em conteúdo vazio")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "HTML vazio após sanitização. Verifique o conteúdo HTML enviado."
                },
            )

        # Gerar PDF em thread separada (non-blocking)
        pdf_bytes = await generate_pdf_async(html_sanitized, request.css)

        logger.info(f"PDF gerado com sucesso: {len(pdf_bytes)} bytes")

        # Retornar PDF com headers apropriados
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="document.pdf"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    except HTTPException:
        raise

    except ValueError as e:
        # Erros de validação (ex: URL bloqueada no custom_url_fetcher)
        logger.warning(f"Erro de validação: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e)},
        ) from e

    except RuntimeError as e:
        # Erros na geração do PDF
        logger.error(f"Erro na geração do PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Falha na geração do PDF. Tente novamente mais tarde."},
        ) from e

    except Exception as e:
        # Erro inesperado
        logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Erro interno do servidor"},
        ) from e


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler customizado para HTTPException que garante resposta em JSON."""
    return StreamingResponse(
        io.BytesIO(
            json.dumps(
                {
                    "error": exc.detail.get("error")
                    if isinstance(exc.detail, dict)
                    else exc.detail,
                    "status_code": exc.status_code,
                }
            ).encode()
        ),
        status_code=exc.status_code,
        media_type="application/json",
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Executar servidor em modo desenvolvimento
    # Produção: usar gunicorn com workers
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,  # Recarregar em mudanças de código (desenvolvimento)
    )
