@REM Teste rápido da API DocGen - Windows (PowerShell/CMD)
@REM
@REM Usage:
@REM  1. Certifique-se que o servidor está rodando: python main.py
@REM  2. Execute este arquivo na raiz do projeto
@REM
@REM Requirements:
@REM  - curl instalado (padrão no Windows 10+)
@REM  - jq (opcional, para parse JSON)

@echo off
setlocal enabledelayedexpansion

echo ============================================
echo      DocGen API - Teste Rápido
echo ============================================
echo.

set API_URL=http://localhost:8000

REM Teste 1: Health Check
echo [1] Teste Health Check...
curl -s -X GET "%API_URL%/health" | more
echo.
echo.

REM Teste 2: PDF Básico
echo [2] Gerando PDF Básico...
curl -s -X POST "%API_URL%/generate-pdf" \
  -H "Content-Type: application/json" \
  -d "{\"html\": \"^<h1^>Olá Mundo^</h1^>\", \"css\": \"h1 { color: red; }\"}" \
  --output "document_basic.pdf"
echo ✓ Arquivo: document_basic.pdf
echo.

REM Teste 3: PDF com Tabela
echo [3] Gerando PDF com Tabela (do arquivo examples_test_advanced.json)...
for /f "tokens=*" %%A in (examples_test_advanced.json) do set PAYLOAD=!PAYLOAD! %%A
curl -s -X POST "%API_URL%/generate-pdf" \
  -H "Content-Type: application/json" \
  -d @examples_test_advanced.json \
  --output "document_tabela.pdf"
echo ✓ Arquivo: document_tabela.pdf
echo.

REM Teste 4: PDF ABNT
echo [4] Gerando PDF com Formatação ABNT (do arquivo examples_test_abnt.json)...
curl -s -X POST "%API_URL%/generate-pdf" \
  -H "Content-Type: application/json" \
  -d @examples_test_abnt.json \
  --output "document_abnt.pdf"
echo ✓ Arquivo: document_abnt.pdf
echo.

REM Teste 5: Segurança (HTML com script - será sanitizado)
echo [5] Testando Sanitização (HTML com script será removido)...
curl -s -X POST "%API_URL%/generate-pdf" \
  -H "Content-Type: application/json" \
  -d @examples_test_security.json \
  --output "document_seguranca.pdf"
echo ✓ Arquivo: document_seguranca.pdf (script foi removido)
echo.

REM Teste 6: Erro - HTML vazio
echo [6] Testando Erro - HTML Vazio...
curl -s -X POST "%API_URL%/generate-pdf" \
  -H "Content-Type: application/json" \
  -d "{\"html\": \"\", \"css\": \"\"}" 
echo.
echo.

echo ============================================
echo      Testes Concluídos!
echo ============================================
echo.
echo PDFs gerados:
dir /b document_*.pdf
echo.
echo Próximos passos:
echo - Abra os arquivos PDF gerados para verificar a qualidade
echo - Verifique os logs no console do servidor
echo - Testar no Thunder Client, Postman, ou similar
echo.
