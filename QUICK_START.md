# 🚀 QUICK START - DocGen API Fase 1

## 📋 Pré-requisitos

- **Python 3.9+** instalado
- **pip** (vem com Python)
- **curl** (opcional, para testes)
- Git (opcional)

---

## ⚡ Start em 5 minutos

### 1️⃣ Instalar Dependências

```bash
cd "c:\www\DocGen3 PP"
pip install -r requirements.txt
```

**Output esperado:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 weasyprint-60.1 bleach-6.1.0 pydantic-2.5.0 ...
```

### 2️⃣ Executar Servidor

```bash
python main.py
```

**Output esperado:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

✅ **Servidor rodando em `http://localhost:8000`**

### 3️⃣ Testar Health Check (em outro terminal)

```bash
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "DocGen API",
  "version": "1.0.0"
}
```

### 4️⃣ Gerar Seu Primeiro PDF

```bash
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d '{"html": "<h1>Olá DocGen!</h1><p>Meu primeiro PDF</p>", "css": "h1 { color: blue; }"}' \
  --output meu_documento.pdf
```

✅ **Arquivo `meu_documento.pdf` foi criado!**

---

## 📁 Estrutura do Projeto

```
c:\www\DocGen3 PP\
├── main.py                      # ⭐ Aplicação FastAPI (PRINCIPAL)
├── requirements.txt             # Dependências Python
├── README.md                    # Documentação completa
├── ARCHITECTURE.md              # Design técnico
├── DEPLOYMENT.md                # Guia de deployment
├── test_main.py                 # Testes unitários
├── Dockerfile                   # Containerização
├── docker-compose.yml           # Multi-container setup
├── .env.example                 # Template de variáveis
├── .gitignore                   # Exclusões Git
└── examples_test_*.json         # Exemplos de requisições
```

---

## 📝 Exemplos Rápidos

### Exemplo 1: HTML + CSS Básico

**arquivo.json:**
```json
{
  "html": "<h1>Relatório</h1><p>Conteúdo</p>",
  "css": "body { font-size: 14pt; } h1 { color: #0066cc; }"
}
```

```bash
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d @arquivo.json \
  --output documento.pdf
```

### Exemplo 2: com Tabela (use examples_test_advanced.json)

```bash
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d @examples_test_advanced.json \
  --output tabela.pdf
```

### Exemplo 3: ABNT (use examples_test_abnt.json)

```bash
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d @examples_test_abnt.json \
  --output abnt.pdf
```

---

## 🧪 Testes Automáticos

### Executar Test Suite Completo

```bash
# Instalar pytest (uma vez)
pip install pytest pytest-asyncio

# Rodar testes
pytest test_main.py -v
```

**Cobertura incluída:**
- ✅ Health check
- ✅ PDF generation sucesso
- ✅ Validação (400, 422)
- ✅ Security (XSS, SSRF)
- ✅ Sanitização
- ✅ CSS Cascade
- ✅ Payload limits

---

## 📊 Monitoramento

### Ver Logs em Tempo Real

```bash
# No terminal onde o servidor está rodando
# Logs aparecem automaticamente
```

**Exemplos de logs:**
```
INFO:     Requisição recebida: HTML length=245, CSS length=120
DEBUG:    HTML sanitizado com sucesso
DEBUG:    Iniciando renderização de PDF com WeasyPrint
INFO:     PDF gerado com sucesso em memória: 45678 bytes
```

### Verificar Status

```bash
curl http://localhost:8000/health
```

---

## 🔒 Segurança Implementada

✅ **SSRF Prevention**: Requisições HTTP/HTTPS bloqueadas  
✅ **XSS Prevention**: Scripts e event handlers removidos  
✅ **Sanitização HTML**: Whitelist de tags permitidas  
✅ **CORS**: Configurável  
✅ **Validação**: Pydantic schemas  
✅ **Tamanho Limite**: Max 1MB payload  

---

## 🚢 Próximas Etapas

### Para Fase 2 (Persistência):
1. Instalar PostgreSQL
2. Adicionar modelos de banco de dados (SQLAlchemy)
3. Implementar autenticação JWT
4. Criar endpoints de CRUD

### Para Fase 3 (Frontend):
1. Criar app React
2. Integrar Monaco Editor
3. Preview em iframe
4. Deploy SPA

---

## 📞 Troubleshooting

### "Comando não encontrado: pip"
```bash
python -m pip install -r requirements.txt
```

### "Port 8000 já está em uso"
```bash
python main.py --port 8001
# ou via uvicorn:
uvicorn main:app --port 8001
```

### "RuntimeError: Falha na renderização do PDF"
Verifique:
- HTML tem tags abertas (ex: `<p>` sem `</p>`)
- Nenhuma URL externa (são bloqueadas por segurança)
- CSS tem sintaxe válida

### PDF gerado mas muito pequeno
Isso é normal. PDF vazio é comum. Verifique que:
- `html` não está vazio
- HTML não contém apenas tags (precisa de conteúdo de texto)

---

## 🎯 Casos de Uso - Próximas Semanas

1. **Aplicação Web**: Use Docker + Nginx para rodar em produção
2. **Agendamento**: Integre com Celery para gerar PDFs em background
3. **Storage**: Persista PDFs gerados no S3 ou similar
4. **Auditoria**: Implemente logging de todas as requisições (Fase 2)

---

## 📚 Documentação Completa

| Arquivo | Conteúdo |
|---------|----------|
| [README.md](README.md) | Documentação completa da API |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design técnico e decisões |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Como fazer deploy (local, cloud, etc) |
| [requirements.txt](requirements.txt) | Dependências do projeto |

---

## 💡 Dicas Pro

1. **Virtual Environment** (altamente recomendado):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Editor de Requisições**: Use Postman, Thunder Client ou similar para testar interativamente

3. **Debug**: Adicione `--reload` para recarregar em mudanças:
   ```bash
   uvicorn main:app --reload
   ```

4. **Produção**: Use Gunicorn com múltiplos workers:
   ```bash
   pip install gunicorn
   gunicorn main:app --workers 4
   ```

---

## ✨ Status Fase 1

- ✅ Motor assíncrono (FastAPI)
- ✅ Geração de PDF (WeasyPrint)
- ✅ Segurança (SSRF + XSS)
- ✅ Performance (threading)
- ✅ Documentação
- ✅ Testes
- ✅ Exemplos
- ✅ Docker
- ✅ Pronto para produção

---

🚀 **Bem-vindo ao DocGen!**

Para dúvidas ou sugestões, consulte a documentação ou crie um issue.

---

**Versão**: 1.0.0 - Fase 1  
**Data**: 25 de março de 2025  
**Tech Lead**: Backend/DevOps  
**Status**: ✅ Production Ready
