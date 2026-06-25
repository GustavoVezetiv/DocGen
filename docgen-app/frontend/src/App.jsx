/*
 * App.jsx - Componente principal do DocGen
 * Interface split-view com Monaco Editor e preview em tempo real
 */
import { useState, useCallback, useRef } from 'react'
import Editor from '@monaco-editor/react'

// ----------------------------------------------------------------
// Conteúdo inicial de exemplo para o editor
// ----------------------------------------------------------------
const INITIAL_HTML = `<h1>Relatório Executivo Q1 2025</h1>

<p>Este documento apresenta os resultados consolidados do primeiro trimestre de 2025, com análise de desempenho financeiro, crescimento de equipe e projeções para o próximo período.</p>

<h2>Resumo Financeiro</h2>

<table>
  <thead>
    <tr>
      <th>Métrica</th>
      <th>Q1 2024</th>
      <th>Q1 2025</th>
      <th>∆ %</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Receita Bruta</td>
      <td>R$ 1.200.000</td>
      <td>R$ 1.850.000</td>
      <td>+54,2%</td>
    </tr>
    <tr>
      <td>Lucro Líquido</td>
      <td>R$ 280.000</td>
      <td>R$ 490.000</td>
      <td>+75,0%</td>
    </tr>
    <tr>
      <td>Novos Clientes</td>
      <td>38</td>
      <td>67</td>
      <td>+76,3%</td>
    </tr>
  </tbody>
</table>

<h2>Destaques do Período</h2>

<ul>
  <li>Lançamento da plataforma <strong>DocGen</strong> com alta adoção inicial.</li>
  <li>Expansão da equipe de engenharia em 12 novos colaboradores.</li>
  <li>Contrato enterprise fechado com grupo hospitalar regional.</li>
</ul>

<blockquote>
  "O crescimento acelerado reflete a solidez da nossa estratégia de produto e a execução disciplinada dos times." — CEO
</blockquote>

<h2>Próximos Passos</h2>

<ol>
  <li>Finalizar migração de infraestrutura para multi-region.</li>
  <li>Lançar módulo de assinatura digital integrado.</li>
  <li>Iniciar programa de parceiros ISV.</li>
</ol>`

const INITIAL_CSS = `/* Estilos locais do documento */
body {
  /* Sobrepõe a fonte padrão para este doc */
  font-family: "Helvetica Neue", Arial, sans-serif;
}

h1 {
  color: #1e40af;
  border-color: #1e40af;
}

h2 {
  color: #1e3a5f;
}

table th {
  background-color: #1e40af;
}

blockquote {
  border-left-color: #1e40af;
  background: #eff6ff;
}`

// ----------------------------------------------------------------
// Constante da URL da API
// ----------------------------------------------------------------
const API_URL = 'http://localhost:8000/generate-pdf'

// ----------------------------------------------------------------
// Componente principal
// ----------------------------------------------------------------
export default function App() {
  // Estado dos editores
  const [html, setHtml]       = useState(INITIAL_HTML)
  const [css, setCss]         = useState(INITIAL_CSS)
  const [activeTab, setActiveTab] = useState('html') // 'html' | 'css'

  // Estado da exportação
  const [exporting, setExporting]     = useState(false)
  const [exportError, setExportError] = useState(null)
  const [exportSuccess, setExportSuccess] = useState(false)

  // Referência do iframe para o live preview
  const iframeRef = useRef(null)

  // Monta o srcDoc do iframe com o HTML + CSS combinados
  const previewDoc = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body {
      font-family: Georgia, serif;
      font-size: 14px;
      line-height: 1.7;
      color: #1a1a1a;
      padding: 40px 48px;
      max-width: 900px;
      margin: 0 auto;
    }
    h1 { font-size: 26px; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-top: 0; }
    h2 { font-size: 18px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; }
    th { background: #2563eb; color: white; padding: 8px 12px; text-align: left; }
    td { padding: 7px 12px; border-bottom: 1px solid #e5e7eb; }
    tr:nth-child(even) td { background: #f8fafc; }
    blockquote { border-left: 4px solid #2563eb; margin: 1em 0; padding: 0.5em 1em; background: #eff6ff; font-style: italic; }
    ul, ol { padding-left: 1.5em; }
    li { margin: 0.3em 0; }
  </style>
  <style>${css}</style>
</head>
<body>${html}</body>
</html>`

  // Dispara o download do PDF gerado pelo backend
  const handleExport = useCallback(async () => {
    setExporting(true)
    setExportError(null)
    setExportSuccess(false)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html, css }),
      })

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}))
        throw new Error(detail?.detail || `Erro HTTP ${response.status}`)
      }

      // Converte a resposta em Blob e aciona o download
      const blob = await response.blob()
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href  = url
      link.download = 'documento.pdf'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err) {
      setExportError(err.message)
    } finally {
      setExporting(false)
    }
  }, [html, css])

  return (
    <div className="flex flex-col h-screen bg-[#0f1117] text-slate-200 select-none">

      {/* ============================================================
          HEADER
      ============================================================ */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-[#2a2d3e] bg-[#1a1d27] shrink-0 z-10">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="font-semibold text-base tracking-tight">
            Doc<span className="text-blue-400">Gen</span>
          </span>
          <span className="hidden sm:inline text-xs text-slate-500 border border-[#2a2d3e] px-2 py-0.5 rounded-full ml-1">
            MVP
          </span>
        </div>

        {/* Controles centrais */}
        <div className="hidden md:flex items-center gap-1 text-xs text-slate-500">
          <svg className="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 8 8">
            <circle cx="4" cy="4" r="3" />
          </svg>
          Preview ao vivo
        </div>

        {/* Botão Exportar */}
        <div className="flex items-center gap-3">
          {exportError && (
            <span className="text-red-400 text-xs max-w-[240px] truncate" title={exportError}>
              ⚠ {exportError}
            </span>
          )}
          {exportSuccess && (
            <span className="text-green-400 text-xs">✓ PDF baixado!</span>
          )}

          <button
            id="btn-export-pdf"
            onClick={handleExport}
            disabled={exporting}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
              transition-all duration-200 shadow-lg
              ${exporting
                ? 'bg-blue-700 cursor-not-allowed opacity-70'
                : 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 hover:shadow-blue-500/25 active:scale-95'
              }
            `}
          >
            {exporting ? (
              <>
                <svg className="w-4 h-4 spinner" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Gerando…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Exportar PDF
              </>
            )}
          </button>
        </div>
      </header>

      {/* ============================================================
          SPLIT VIEW PRINCIPAL
      ============================================================ */}
      <div className="flex flex-1 overflow-hidden">

        {/* ---- PAINEL ESQUERDO: Editores ---- */}
        <div className="flex flex-col w-1/2 border-r border-[#2a2d3e] overflow-hidden">

          {/* Abas HTML / CSS */}
          <div className="flex items-center bg-[#1a1d27] border-b border-[#2a2d3e] shrink-0">
            <TabButton
              id="tab-html"
              label="HTML"
              icon={
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              }
              active={activeTab === 'html'}
              onClick={() => setActiveTab('html')}
              color="blue"
            />
            <TabButton
              id="tab-css"
              label="CSS"
              icon={
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
              }
              active={activeTab === 'css'}
              onClick={() => setActiveTab('css')}
              color="indigo"
            />

            {/* contador de linhas */}
            <div className="ml-auto px-4 text-xs text-slate-600 hidden sm:block">
              {activeTab === 'html'
                ? `${html.split('\n').length} linhas`
                : `${css.split('\n').length} linhas`}
            </div>
          </div>

          {/* Monaco Editor – HTML */}
          <div className={`flex-1 overflow-hidden ${activeTab !== 'html' ? 'hidden' : ''}`}>
            <Editor
              height="100%"
              defaultLanguage="html"
              theme="vs-dark"
              value={html}
              onChange={(val) => setHtml(val ?? '')}
              options={{
                fontSize: 13,
                fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
                fontLigatures: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 12, bottom: 12 },
                lineNumbersMinChars: 3,
                renderLineHighlight: 'line',
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
              }}
            />
          </div>

          {/* Monaco Editor – CSS */}
          <div className={`flex-1 overflow-hidden ${activeTab !== 'css' ? 'hidden' : ''}`}>
            <Editor
              height="100%"
              defaultLanguage="css"
              theme="vs-dark"
              value={css}
              onChange={(val) => setCss(val ?? '')}
              options={{
                fontSize: 13,
                fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
                fontLigatures: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 12, bottom: 12 },
                lineNumbersMinChars: 3,
                renderLineHighlight: 'line',
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
              }}
            />
          </div>
        </div>

        {/* ---- PAINEL DIREITO: Live Preview ---- */}
        <div className="flex flex-col w-1/2 overflow-hidden bg-[#e8eaf0]">
          {/* Barra do preview */}
          <div className="flex items-center justify-between px-4 py-2 bg-[#1a1d27] border-b border-[#2a2d3e] shrink-0">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Live Preview
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500 opacity-60" />
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-500 opacity-60" />
              <div className="w-2.5 h-2.5 rounded-full bg-green-500 opacity-60" />
              <span className="ml-2 hidden sm:inline">documento.pdf</span>
            </div>
          </div>

          {/* iframe do preview A4 */}
          <div className="flex-1 overflow-auto bg-[#64748b] flex justify-center py-6 px-4">
            <div
              style={{
                width: '794px',           /* ~A4 em 96 dpi */
                minHeight: '1123px',      /* A4 altura */
                flexShrink: 0,
                boxShadow: '0 8px 40px rgba(0,0,0,0.45)',
                borderRadius: '2px',
              }}
            >
              <iframe
                ref={iframeRef}
                id="preview-iframe"
                title="Live Preview"
                srcDoc={previewDoc}
                className="preview-frame"
                style={{ width: '100%', height: '100%', minHeight: '1123px', border: 'none' }}
                sandbox="allow-same-origin"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================
          STATUSBAR
      ============================================================ */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#1a1d27] border-t border-[#2a2d3e] shrink-0">
        <div className="flex items-center gap-4 text-xs text-slate-600">
          <span>DocGen v1.0</span>
          <span className="hidden sm:inline">·</span>
          <span className="hidden sm:inline">WeasyPrint backend</span>
        </div>
        <div className="text-xs text-slate-600">
          A4 · 96 dpi preview
        </div>
      </div>

    </div>
  )
}

// ----------------------------------------------------------------
// Componente auxiliar: botão de aba
// ----------------------------------------------------------------
function TabButton({ id, label, icon, active, onClick, color }) {
  const activeColors = {
    blue:   'border-blue-500 text-blue-400 bg-[#0f1117]',
    indigo: 'border-indigo-500 text-indigo-400 bg-[#0f1117]',
  }
  const inactiveStyle = 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-[#0f1117]/40'

  return (
    <button
      id={id}
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium
        border-b-2 transition-all duration-150
        ${active ? activeColors[color] : inactiveStyle}
      `}
    >
      {icon}
      {label}
    </button>
  )
}
