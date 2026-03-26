# DocGen - Fase 1: Motor Stateless

## Arquitetura da Solução

### Componentes Principais

1. **FastAPI Application**
   - Assíncrona (non-blocking)
   - CORS habilitado para desenvolvimento
   - Validação de payload com limite de 1MB

2. **Security Layer**
   - **Sanitização HTML:** Bleach remove tags e atributos perigosos (XSS Prevention)
   - **SSRF Prevention:** `custom_url_fetcher` bloqueia `file://` e URLs externas
   - **Validação Pydantic:** Schemas tipados com Field validators

3. **PDF Generation (Non-Blocking)**
   - WeasyPrint executa em **thread separada** via `asyncio.to_thread()`
   - Renderização: `CSS_GLOBAL` → `CSS_LOCAL` → `HTML_USER` (Cascade garantido)
   - PDF em memória (`io.BytesIO`) - zero I/O em disco

4. **Error Handling**
   - 400: JSON inválido, validação falhou, payload grande
   - 422: Entidade não processável (Pydantic)
   - 500: Erro na geração do PDF
   - Sempre respostas em JSON padronizado

---

## Setup & Execução

### 1. Criar ambiente virtual (opcional mas recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

**Dependências:**
- `fastapi==0.104.1` - Framework web assíncrono
- `uvicorn==0.24.0` - ASGI server
- `weasyprint==60.1` - Motor de PDF (HTML + CSS → PDF)
- `bleach==6.1.0` - Sanitização de HTML
- `pydantic==2.5.0` - Validação de dados
- `python-multipart==0.0.6` - Suporte a multipart/form-data

### 3. Executar servidor

```bash
python main.py
```

ou com Uvicorn diretamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Servidor estará disponível em: `http://localhost:8000`

---

## API Reference

### Health Check

**GET** `/health`

Verifica se o serviço está rodando.

**Response:**
```json
{
  "status": "healthy",
  "service": "DocGen API",
  "version": "1.0.0"
}
```

---

### Generate PDF

**POST** `/generate-pdf`

Processa HTML + CSS e retorna PDF.

#### Request Body

```json
{
  "html": "<h1>Título do Documento</h1><p>Conteúdo aqui</p>",
  "css": "h1 { color: #0066cc; font-size: 28pt; }"
}
```

**Campos:**
- `html` (string, obrigatório): HTML do documento. Será sanitizado (XSS prevention)
- `css` (string, opcional): CSS customizado do usuário. O CSS Global é injetado automaticamente.

**Limits:**
- Payload máximo: 1MB (total JSON)
- HTML máximo: 1MB
- CSS máximo: 100KB

#### Response

**Success (200 OK):**
- Content-Type: `application/pdf`
- Header: `Content-Disposition: attachment; filename="document.pdf"`
- Body: PDF binário

**Client Error (400 Bad Request):**
```json
{
  "error": "Payload muito grande. Máximo: 1.0MB",
  "status_code": 400
}
```

**Validation Error (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "html"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Server Error (500 Internal Server Error):**
```json
{
  "error": "Falha na geração do PDF. Tente novamente mais tarde.",
  "status_code": 500
}
```

---

## Exemplos de Uso

### cURL

```bash
# POST simples
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<h1>Olá Mundo</h1>",
    "css": "h1 { color: red; }"
  }' \
  --output document.pdf

# COM CSS mais complexo
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<div class=\"container\"><h1>Relatório</h1><p>Texto do relatório</p></div>",
    "css": ".container { max-width: 800px; margin: 0 auto; padding: 20px; } h1 { font-size: 24pt; color: #333; }"
  }' \
  --output relatorio.pdf
```

### Python (requests)

```python
import requests

url = "http://localhost:8000/generate-pdf"

payload = {
    "html": """
    <h1>Documento Oficial</h1>
    <p>Este é um documento gerado dinamicamente.</p>
    <table>
        <tr><th>Coluna 1</th><th>Coluna 2</th></tr>
        <tr><td>A</td><td>B</td></tr>
    </table>
    """,
    "css": """
    body { font-family: Arial, sans-serif; }
    h1 { color: #0066cc; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; }
    table th, table td { border: 1px solid #ccc; padding: 8px; }
    table th { background-color: #f0f0f0; }
    """
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    with open("documento.pdf", "wb") as f:
        f.write(response.content)
    print("PDF gerado com sucesso!")
else:
    print(f"Erro: {response.status_code}")
    print(response.json())
```

### JavaScript (fetch)

```javascript
async function generatePDF() {
  const payload = {
    html: `
      <h1>Exemplo JavaScript</h1>
      <p>Gerado via JavaScript com fetch API</p>
    `,
    css: `
      body { font-size: 12pt; }
      h1 { color: #0066cc; }
    `
  };

  try {
    const response = await fetch('http://localhost:8000/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'document.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } else {
      const error = await response.json();
      console.error('Erro:', error);
    }
  } catch (err) {
    console.error('Erro na requisição:', err);
  }
}
```

---

## Testes Locais (Thunder Client, Postman, ou similar)

### Request básica

```
POST http://localhost:8000/generate-pdf
Content-Type: application/json

{
  "html": "<h1>Test</h1>",
  "css": "body { background: white; }"
}
```

### Request com ABNT Style

```json
{
  "html": "<h1>DOCUMENTO ABNT</h1><p>Texto formatado conforme normas ABNT.</p>",
  "css": "body { line-height: 1.5; font-size: 12pt; margin: 2cm; }"
}
```

---

## Regras de Negócio Implementadas

### 1. Injeção de CSS (Cascade)

```
┌─────────────────────────┐
│  <style>CSS_GLOBAL</style>  │  ← Design System (não editável)
├─────────────────────────┤
│  <style>CSS_LOCAL</style>   │  ← User CSS (customização)
├─────────────────────────┤
│  HTML_USER              │  ← Conteúdo do usuário
└─────────────────────────┘
```

O CSS Local **sobrescreve** o CSS Global (Cascade CSS).

### 2. Sanitização HTML

**Tags permitidas:**
`p, br, strong, em, u, strike, code, pre, h1-h6, ul, ol, li, blockquote, table, a, img, span, div, hr, section, article, header, footer, nav`

**Tags bloqueadas (XSS Prevention):**
`script, iframe, object, embed, style, link, meta, form, input, button, select, textarea, ...`

**Atributos removidos:**
- `onclick`, `onload`, `onerror`, etc. (event handlers)
- `javascript:` URLs

### 3. SSRF Prevention (URL Fetcher Customizado)

**Bloqueado:**
- `file:///` - Acesso a arquivos locais
- `http://`, `https://` - Requisições externas
- `ftp://`, `sftp://` - Protocols remotos

**Permitido:**
- `data:image/...` - Data URLs inline (base64, SVG, etc.)

### 4. Performance (Non-Blocking)

WeasyPrint (CPU-bound) executa em thread separada via `asyncio.to_thread()`:
- Event Loop do FastAPI **não trava**
- Requisições simultâneas processadas paralelamente
- Escalabilidade horizontal com múltiplos workers

---

## Configurações de Produção

### 1. Desabilitar reload

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload=False
```

### 2. Usar Gunicorn com workers

```bash
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### 3. Variáveis de Ambiente (próximas fases)

```bash
export MAX_PAYLOAD_SIZE=2097152  # 2MB
export LOG_LEVEL=WARNING
export CORS_ORIGINS="https://app.docgen.com"
```

---

## Logging

Logs são emitidos no nível `INFO` por padrão:

```
2025-03-25 10:15:30,123 - main - INFO - Requisição recebida: HTML length=245, CSS length=120
2025-03-25 10:15:30,450 - main - DEBUG - HTML sanitizado com sucesso
2025-03-25 10:15:30,750 - main - DEBUG - Iniciando renderização de PDF com WeasyPrint
2025-03-25 10:15:31,200 - main - INFO - PDF gerado com sucesso em memória: 45678 bytes
```

---

## Próximas Fases

### Fase 2: Persistência e Autenticação
- PostgreSQL para armazenar templates e documentos
- JWT authentication
- Endpoint `GET /documents/{id}`
- Rate limiting por usuário

### Fase 3: Frontend SPA
- React com Monaco Editor
- Preview real-time em iframe
- Histórico de versões
- Colaboração em tempo real (WebSocket)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'weasyprint'"
```bash
pip install -r requirements.txt
```

### "RuntimeError: Falha na renderização do PDF"
Verifique:
- HTML válido (tags abertas/fechadas corretamente)
- CSS válido (sintaxe correcta)
- Nenhuma URL externa no HTML/CSS

### "Payload muito grande"
Reduzir tamanho do HTML/CSS ou aumentar `MAX_PAYLOAD_SIZE` em `main.py`

### Requisição externa bloqueada
O sistema bloqueia intencionalmente `http://`, `https://` e `file://` por segurança (SSRF Prevention).
Use `data:image/png;base64,...` para imagens inline.

---

## Suporte e Roadmap

**Email:** dev@docgen.local
**GitHub:** github.com/docgen/docgen-api
**Docs:** https://docs.docgen.local/api/v1

---

Versão: 1.0.0 (Fase 1 - Motor Stateless)
Data: 2025-03-25
Tech Lead: Backend/DevOps
