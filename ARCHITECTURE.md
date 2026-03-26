# ARQUITETURA - DocGen API Fase 1

## 1. Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    Cliente (Frontend)                        │
│              React + Monaco Editor (Fase 3)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP POST /generate-pdf
                    (JSON: html, css)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (Async)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CORS Middleware (allow_origins=["*"])              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Payload Size Limit (1MB)                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Pydantic Validation (GeneratePDFRequest)           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Sanitization (Bleach - XSS Prevention)             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  async generate_pdf_async()                         │   │
│  │  └─ asyncio.to_thread(PDF_GENERATION)              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                   asyncio.to_thread()
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Thread Pool (Non-blocking)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CSS Injection Layer                                │   │
│  │  • CSS_GLOBAL (Design System)                       │   │
│  │  • CSS_LOCAL (User Custom)                          │   │
│  │  • HTML_USER (Sanitized)                            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  WeasyPrint PDF Generation                          │   │
│  │  • custom_url_fetcher (SSRF Prevention)             │   │
│  │  • HTML string → PDF bytes                          │   │
│  │  • BytesIO (in-memory, no disk I/O)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                  PDF bytes (io.BytesIO)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Response (Streaming)                    │
│  Content-Type: application/pdf                              │
│  Content-Disposition: attachment; filename="document.pdf"  │
│  Cache-Control: no-cache                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                   HTTP 200 + PDF bytes
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cliente (Download)                        │
│                   documento.pdf                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológico

### 2.1 Core
- **Framework**: FastAPI 0.104.1 (ASGI, async/await)
- **Server**: Uvicorn 0.24.0 (ASGI server)
- **PDF Engine**: WeasyPrint 60.1 (HTML/CSS → PDF)
- **Validation**: Pydantic 2.5.0 (Type safety, schema validation)
- **Sanitization**: Bleach 6.1.0 (XSS prevention)

### 2.2 Infraestrutura (Próximas Fases)
- **Database**: PostgreSQL (Fase 2)
- **Cache**: Redis (Fase 3)
- **Frontend**: React (Fase 3)
- **API Gateway**: Nginx/CloudFlare (Production)
- **Container**: Docker/K8s (Production)

---

## 3. Componentes Principais

### 3.1 Request Body (Pydantic Model)

```python
class GeneratePDFRequest(BaseModel):
    html: str  # Obrigatório, max 1MB
    css: Optional[str] = ""  # Opcional, max 100KB
```

**Validações:**
- HTML não pode ser vazio após strip
- CSS é opcional (default = "")
- Ambos têm limite de tamanho

### 3.2 Security Layer

#### 3.2.1 HTML Sanitization (Bleach)

**Função**: `sanitize_html(html: str) → str`

**Whitelist de Tags Permitidas**:
```
p, br, strong, em, u, strike, code, pre, h1-h6, ul, ol, li, 
blockquote, table, thead, tbody, tr, th, td, a, img, span, div, 
hr, section, article, header, footer, nav
```

**Tags Bloqueadas** (XSS Prevention):
```
script, iframe, object, embed, style, link, meta, form, input, 
button, select, textarea, applet, base, frameset, etc.
```

**Atributos Removidos**:
- Event handlers: `onclick`, `onload`, `onerror`, etc.
- Dangerous URLs: `javascript:`, `data:`

#### 3.2.2 SSRF Prevention (custom_url_fetcher)

**Função**: `custom_url_fetcher(url: str) → raises ValueError`

**Bloqueado**:
- `file:///` (Local file access)
- `http://`, `https://` (External requests)
- `ftp://`, `sftp://` (Remote protocols)

**Permitido**:
- `data:image/...` (Base64 inline images)
- `data:text/...` (SVG inline)

### 3.3 PDF Generation (Non-Blocking)

#### 3.3.1 Flow

```
1. Input: html (sanitized), css_user (custom)
        ↓
2. HTML Injection:
   <!DOCTYPE html>
   <html>
   <head>
     <style>{CSS_GLOBAL}</style>    ← Design System
     <style>{CSS_USER}</style>      ← User Custom
   </head>
   <body>
     {HTML_USER}                     ← Sanitized user HTML
   </body>
   </html>
        ↓
3. WeasyPrint Rendering:
   HTML(string=final_html).write_pdf(BytesIO)
        ↓
4. Output: PDF bytes (io.BytesIO)
        ↓
5. Response: StreamingResponse (PDF binary)
```

#### 3.3.2 Async Execution

```python
# Event Loop (FastAPI)
async def generate_pdf(request):
    pdf_bytes = await asyncio.to_thread(
        _generate_pdf_sync,  # Sync function
        html,
        css_global,
        css_user
    )
    # Event loop não trava durante renderização
```

**Benefício**: Event loop processa outras requisições enquanto PDF é gerado em thread separada.

### 3.4 CSS Global (Design System)

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12pt;
    color: #333;
    line-height: 1.5;
}

/* Headings, tables, links, etc... */

@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: "Página " counter(page) " de " counter(pages);
    }
}
```

**Características**:
- Reset CSS default styles
- Typography base
- Page setup (A4, margins, footer numeração)
- Não editável pelo usuário
- Pode ser customizado por Admin (Fase 2)

---

## 4. Error Handling

### 4.1 HTTP Status Codes

| Status | Trigger | Response |
|--------|---------|----------|
| 200 | PDF gerado com sucesso | `StreamingResponse(PDF bytes)` |
| 400 | HTML vazio, payload grande, validação | `{"error": "msg"}` |
| 413 | Payload > MAX_SIZE | `{"error": "Payload muito grande"}` |
| 422 | Pydantic validation falha | `{"detail": [validation errors]}` |
| 500 | Erro durante PDF generation | `{"error": "Falha na renderização"}` |

### 4.2 Logging

```python
logger.info("Requisição recebida: HTML length=245")
logger.debug("HTML sanitizado com sucesso")
logger.debug("Iniciando renderização de PDF")
logger.info("PDF gerado com sucesso: 45678 bytes")
logger.warning("Tentativa de acesso bloqueada: file:// protocol")
logger.error("Erro ao gerar PDF: ...", exc_info=True)
```

---

## 5. Performance Considerations

### 5.1 PDF Generation (CPU-bound)
- WeasyPrint é síncrono e CPU-intensivo
- Executa em thread separada (não honra Event Loop)
- Tipicamente ~500ms-2s por PDF (depende do tamanho/complexidade)

### 5.2 Concurrency Model

```
┌─ Req 1 (HTML1, CSS1) → Thread 1 → PDF1
│
├─ Req 2 (HTML2, CSS2) → Thread 2 → PDF2  (Simultânea!)
│
├─ Req 3 (HTML3, CSS3) → Thread 3 → PDF3
│
└─ Event Loop (FastAPI) → Processa outras requisições
```

**Escalabilidade**:
- 1 uvicorn worker = 1 Event Loop + Thread Pool
- Múltiplos workers = múltiplos Event Loops (Gunicorn)
- Load Balancer distribui requisições entre workers

### 5.3 Memory Usage

- JSON parsing: ~O(payload_size)
- HTML sanitization: ~O(html_size)
- PDF generation: ~O(pdf_size) em `BytesIO`
- Limite: 1MB payload → ~5-10MB PDF max

---

## 6. Roadmap Fases

### Fase 1 (Atual): Motor Stateless ✅
- [x] API FastAPI pura
- [x] HTML/CSS → PDF
- [x] Security (SSRF, XSS)
- [x] Performance (non-blocking)
- [x] Error handling

### Fase 2: Persistência + Auth
- [ ] PostgreSQL integration
- [ ] JWT authentication
- [ ] Template storage
- [ ] Document history
- [ ] User management

### Fase 3: Frontend SPA
- [ ] React app
- [ ] Monaco Editor
- [ ] Real-time preview
- [ ] Collaboration (WebSocket)
- [ ] Version control

### Fase 4+: Enterprise
- [ ] Multi-tenant support
- [ ] Advanced templates (conditional rendering)
- [ ] Payment integration
- [ ] Analytics
- [ ] API analytics

---

## 7. Deployment Architecture

### 7.1 Development

```
Developer Machine
│
├─ venv (virtual env)
├─ main.py (uvicorn --reload)
├─ SQLite (local)
└─ Logs (console)
```

### 7.2 Production

```
Client Browser
     │
     └─ HTTPS
          │
          ▼
    Cloudflare/CDN
          │
          ▼
    Load Balancer (Nginx)
     │   │   │
     ├───┼───┤
     ▼   ▼   ▼
  Worker1 Worker2 Worker3
  (Gunicorn + Uvicorn)
     │   │   │
     └───┼───┘
         ▼
    PostgreSQL (RDS)
    Redis (Cache)
    S3 (Storage - Fase 3+)
```

---

## 8. Compliance & Security

- **SSRF Prevention**: Custom URL fetcher blocks external URLs
- **XSS Prevention**: Bleach sanitization
- **CORS**: Configurable for development/production
- **SSL/TLS**: Enforced in production
- **Rate Limiting**: To be implemented (Fase 2)
- **Audit Logging**: To be implemented (Fase 2)

---

## 9. Monitoring & Observability

### 9.1 Metrics to Monitor
- Request count (per endpoint)
- Response time (p50, p95, p99)
- Error rate (by status code)
- PDF generation time
- Memory usage
- CPU usage

### 9.2 Logging Strategy
- Structured JSON logs (future)
- Centralized logging (ELK, Datadog)
- Error tracking (Sentry)
- APM (Application Performance Monitoring)

---

Arquiteto: Tech Lead Backend/DevOps
Versão: 1.0.0 Fase 1
Data: 2025-03-25
