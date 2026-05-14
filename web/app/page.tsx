'use client'

import { useState } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────
type Variant = 'A' | 'B' | 'C'

interface Diagnostic { stage: number; severity: string; lineNo: number; message: string }
interface ValidationResult {
  parseOk: boolean; ssaOk: boolean; cfOk: boolean; allOk: boolean
  errors: string[]; warnings: string[]
  stage1Errors: Diagnostic[]; stage2Errors: Diagnostic[]; stage3Errors: Diagnostic[]
}
interface ComparisonResult {
  gtText: string; blockMatch: boolean; missingBlocks: string[]; extraBlocks: string[]
  phiMatch: boolean; gtPhis: number; llmPhis: number; fnMatch: boolean; gtFns: string[]; llmFns: string[]
}
interface PipelineResult {
  source: string; prompt: string; rawOutput: string; ir: string
  validation: ValidationResult; comparison: ComparisonResult | null
}
interface RepairAttempt { cycle: number; ir: string; validation: ValidationResult }

// ─── Constants ────────────────────────────────────────────────────────────────
const CONSTRUCTS = [
  { id: '01', name: 'var_decl',    label: 'Variable Declarations', difficulty: 'Easy',   color: 'text-emerald-400' },
  { id: '02', name: 'expressions', label: 'Expressions',           difficulty: 'Easy',   color: 'text-emerald-400' },
  { id: '03', name: 'if_else',     label: 'If / Else Branch',      difficulty: 'Medium', color: 'text-yellow-400'  },
  { id: '04', name: 'while_loop',  label: 'While Loop',            difficulty: 'Medium', color: 'text-yellow-400'  },
  { id: '05', name: 'for_loop',    label: 'For Loop',              difficulty: 'Medium', color: 'text-yellow-400'  },
  { id: '06', name: 'functions',   label: 'Functions',             difficulty: 'Medium', color: 'text-yellow-400'  },
  { id: '07', name: 'nested_ctrl', label: 'Nested If in While',    difficulty: 'Hard',   color: 'text-red-400'     },
]

const VARIANT_INFO = {
  A: { label: 'Minimal',    desc: 'Just ask. No rules given. Gemini must know everything itself.' },
  B: { label: 'Rule-based', desc: 'All 6 LLVM IR rules injected into the prompt.' },
  C: { label: 'Few-shot',   desc: 'Rules + one worked if/else example given.' },
}

// ─── Small components ─────────────────────────────────────────────────────────

function CodeBlock({ code, maxH = '400px' }: { code: string; maxH?: string }) {
  return (
    <pre
      className="code-block bg-slate-900 border border-slate-700 rounded-lg p-4 overflow-auto text-slate-300"
      style={{ maxHeight: maxH }}
    >
      {code}
    </pre>
  )
}

function StepHeader({ num, title, status }: { num: number; title: string; status?: 'pass' | 'fail' | 'pending' | null }) {
  const badge = status === 'pass'
    ? <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-emerald-900 text-emerald-300 font-semibold">PASS</span>
    : status === 'fail'
    ? <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-red-900 text-red-300 font-semibold">FAIL</span>
    : null
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
        {num}
      </span>
      <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">{title}</h2>
      {badge}
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-xl p-5 mb-4 ${className}`}>
      {children}
    </div>
  )
}

function StageRow({ label, ok, skipped, errors }: { label: string; ok: boolean; skipped?: boolean; errors: Diagnostic[] }) {
  const icon = skipped ? '—' : ok ? '✓' : '✗'
  const color = skipped ? 'text-slate-500' : ok ? 'text-emerald-400' : 'text-red-400'
  const statusText = skipped ? 'SKIPPED' : ok ? 'PASS' : 'FAIL'
  return (
    <div className="mb-3">
      <div className="flex items-center gap-3">
        <span className={`text-lg font-bold w-5 text-center ${color}`}>{icon}</span>
        <span className="text-sm text-slate-300 flex-1">{label}</span>
        <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
          skipped ? 'bg-slate-800 text-slate-500' :
          ok ? 'bg-emerald-900/50 text-emerald-300' : 'bg-red-900/50 text-red-300'
        }`}>{statusText}</span>
      </div>
      {!ok && !skipped && errors.map((e, i) => (
        <div key={i} className="ml-8 mt-1 text-xs text-red-300 bg-red-950/40 border border-red-900/40 rounded px-2 py-1 font-mono">
          {e.message}
        </div>
      ))}
    </div>
  )
}

function ValidationPanel({ v }: { v: ValidationResult }) {
  return (
    <div>
      <StageRow label="Stage 1 — Syntax Check"    ok={v.parseOk} errors={v.stage1Errors} />
      <StageRow label="Stage 2 — SSA / Type Check" ok={v.ssaOk}   skipped={!v.parseOk} errors={v.stage2Errors} />
      <StageRow label="Stage 3 — Control Flow"     ok={v.cfOk}    skipped={!v.parseOk} errors={v.stage3Errors} />
      <div className={`mt-4 p-3 rounded-lg text-sm font-semibold ${v.allOk ? 'bg-emerald-900/40 text-emerald-300 border border-emerald-800' : 'bg-red-900/40 text-red-300 border border-red-800'}`}>
        {v.allOk
          ? '✓  All stages passed — the IR is structurally valid!'
          : `✗  Failed with ${v.errors.length} error(s) — see above`}
      </div>
      {v.warnings.length > 0 && (
        <div className="mt-2 text-xs text-yellow-400 font-mono">{v.warnings.length} warning(s): {v.warnings[0]}</div>
      )}
    </div>
  )
}

function ComparisonPanel({ c }: { c: ComparisonResult }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className={`p-2 rounded ${c.fnMatch ? 'bg-emerald-900/30 text-emerald-300' : 'bg-red-900/30 text-red-300'}`}>
          {c.fnMatch ? '✓' : '✗'} Functions: {c.llmFns.join(', ') || 'none'}
        </div>
        <div className={`p-2 rounded ${c.blockMatch ? 'bg-emerald-900/30 text-emerald-300' : 'bg-red-900/30 text-red-300'}`}>
          {c.blockMatch ? '✓' : '✗'} Blocks: {c.blockMatch ? 'match' : `missing [${c.missingBlocks.join(', ')}]`}
        </div>
        <div className={`p-2 rounded ${c.phiMatch ? 'bg-emerald-900/30 text-emerald-300' : 'bg-red-900/30 text-red-300'}`}>
          {c.phiMatch ? '✓' : '✗'} Phi nodes: GT={c.gtPhis} / Gemini={c.llmPhis}
          {!c.phiMatch && c.llmPhis < c.gtPhis && <span className="block text-xs mt-0.5">⚠ Missing {c.gtPhis - c.llmPhis} phi node(s) — #1 failure mode</span>}
        </div>
      </div>
      <details className="mt-3">
        <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300">Show ground truth IR ▸</summary>
        <CodeBlock code={c.gtText} maxH="280px" />
      </details>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function Home() {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [useCustom, setUseCustom]     = useState(false)
  const [customCode, setCustomCode]   = useState(`func max_val(a: int, b: int) -> int {\n  int result = 0;\n  if (a > b) {\n    result = a;\n  } else {\n    result = b;\n  }\n  return result;\n}`)
  const [variant, setVariant]         = useState<Variant>('A')
  const [isRunning, setIsRunning]     = useState(false)
  const [result, setResult]           = useState<PipelineResult | null>(null)
  const [repairs, setRepairs]         = useState<RepairAttempt[]>([])
  const [isRepairing, setIsRepairing] = useState(false)
  const [error, setError]             = useState<string | null>(null)

  const selected = selectedIdx !== null ? CONSTRUCTS[selectedIdx] : null

  async function handleRun() {
    if (!useCustom && selectedIdx === null) return
    setIsRunning(true)
    setResult(null)
    setRepairs([])
    setError(null)
    try {
      const body = useCustom
        ? { customCode, variant }
        : { constructId: selected!.id, constructName: selected!.name, variant }
      const res = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setResult(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIsRunning(false)
    }
  }

  async function handleRepair() {
    if (!result) return
    const currentIR = repairs.length > 0 ? repairs[repairs.length - 1].ir : result.ir
    const currentErrors = repairs.length > 0 ? repairs[repairs.length - 1].validation.errors : result.validation.errors
    setIsRepairing(true)
    try {
      const res = await fetch('/api/repair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: result.source, ir: currentIR, errors: currentErrors }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setRepairs(prev => [...prev, { cycle: prev.length + 1, ir: data.ir, validation: data.validation }])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIsRepairing(false)
    }
  }

  const latestValidation = repairs.length > 0 ? repairs[repairs.length - 1].validation : result?.validation
  const latestIR         = repairs.length > 0 ? repairs[repairs.length - 1].ir         : result?.ir
  const canRepair        = result && !latestValidation?.allOk && repairs.length < 3

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <aside className="w-72 flex-shrink-0 border-r border-slate-800 flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-base font-bold text-white">LLM Compiler Lowering</h1>
          <p className="text-xs text-slate-400 mt-1">Assignment 15 — Interactive Demo</p>
        </div>

        <div className="p-4 flex-1">
          {/* Construct picker */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Pick a Program</p>
          <div className="space-y-1 mb-4">
            {CONSTRUCTS.map((c, i) => (
              <button
                key={c.id}
                onClick={() => { setSelectedIdx(i); setUseCustom(false); setResult(null); setRepairs([]) }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  !useCustom && selectedIdx === i
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <span className="font-mono text-xs text-slate-500 mr-1">{c.id}</span>
                <span>{c.label}</span>
                <span className={`float-right text-xs ${c.color}`}>{c.difficulty}</span>
              </button>
            ))}
            <button
              onClick={() => { setUseCustom(true); setSelectedIdx(null); setResult(null); setRepairs([]) }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                useCustom ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <span className="font-mono text-xs mr-1">✎</span> Custom Code
            </button>
          </div>

          {/* Variant picker */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Prompt Style</p>
          <div className="space-y-1 mb-5">
            {(['A', 'B', 'C'] as Variant[]).map(v => (
              <button
                key={v}
                onClick={() => setVariant(v)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  variant === v ? 'bg-purple-700 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <span className="font-mono font-bold mr-2">{v}</span>
                <span>{VARIANT_INFO[v].label}</span>
              </button>
            ))}
          </div>
          {variant && (
            <p className="text-xs text-slate-500 mb-5 px-1">{VARIANT_INFO[variant].desc}</p>
          )}

          {/* Run button */}
          <button
            onClick={handleRun}
            disabled={isRunning || (!useCustom && selectedIdx === null)}
            className="w-full py-3 rounded-xl font-semibold text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? '⏳  Calling Gemini...' : '▶  Run Pipeline'}
          </button>

          {error && (
            <div className="mt-3 p-2 bg-red-900/40 border border-red-800 rounded text-xs text-red-300">{error}</div>
          )}
        </div>

        {/* Pipeline legend */}
        <div className="p-4 border-t border-slate-800 text-xs text-slate-500 space-y-1">
          <p className="font-semibold text-slate-400 mb-1">Pipeline Steps</p>
          <p>1 Source code</p>
          <p>2 Prompt sent to Gemini</p>
          <p>3 Gemini's LLVM IR output</p>
          <p>4 Validator (3 stages)</p>
          <p>5 Ground truth comparison</p>
          <p>6 Repair loop (up to 3×)</p>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto p-6">

        {/* Custom code editor */}
        {useCustom && (
          <Card>
            <StepHeader num={0} title="Your Custom Program" />
            <p className="text-xs text-slate-400 mb-2">Write any program in the custom C-like language, then click Run.</p>
            <textarea
              value={customCode}
              onChange={e => setCustomCode(e.target.value)}
              className="w-full h-48 code-block bg-slate-950 border border-slate-700 rounded-lg p-3 text-slate-300 focus:outline-none focus:border-blue-500 resize-y"
              spellCheck={false}
            />
          </Card>
        )}

        {/* Empty state */}
        {!result && !isRunning && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-600">
            <div className="text-5xl mb-4">⚙</div>
            <p className="text-lg font-semibold">Pick a program and click Run</p>
            <p className="text-sm mt-1">The full pipeline will appear here step by step</p>
          </div>
        )}

        {/* Loading */}
        {isRunning && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <div className="text-4xl mb-4 animate-spin">⟳</div>
            <p>Calling Gemini API...</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Step 1: Source */}
            <Card>
              <StepHeader num={1} title="Source Code" />
              <p className="text-xs text-slate-500 mb-2">
                The C-like program we're asking Gemini to translate into LLVM IR.
              </p>
              <CodeBlock code={result.source} />
            </Card>

            {/* Step 2: Prompt */}
            <Card>
              <StepHeader num={2} title={`Prompt Sent to Gemini  (Variant ${variant})`} />
              <p className="text-xs text-slate-500 mb-2">
                {VARIANT_INFO[variant].desc}
              </p>
              <details>
                <summary className="text-xs text-blue-400 cursor-pointer hover:text-blue-300 mb-2">Show full prompt ▸</summary>
                <CodeBlock code={result.prompt} maxH="280px" />
              </details>
            </Card>

            {/* Step 3: Generated IR */}
            <Card>
              <StepHeader num={3} title="Gemini's Generated LLVM IR" />
              <p className="text-xs text-slate-500 mb-2">
                This is what Gemini produced. Now we check if it follows all LLVM IR rules.
              </p>
              <CodeBlock code={result.ir} />
            </Card>

            {/* Step 4: Validation */}
            <Card>
              <StepHeader num={4} title="Validator Results" status={result.validation.allOk ? 'pass' : 'fail'} />
              <p className="text-xs text-slate-500 mb-3">
                3-stage structural check: syntax → SSA/types → control flow.
              </p>
              <ValidationPanel v={result.validation} />
            </Card>

            {/* Step 5: Ground truth */}
            {result.comparison && (
              <Card>
                <StepHeader num={5} title="Ground Truth Comparison" />
                <p className="text-xs text-slate-500 mb-3">
                  Comparing Gemini's output structure against the hand-written correct IR.
                </p>
                <ComparisonPanel c={result.comparison} />
              </Card>
            )}

            {/* Step 6: Repair loop */}
            <Card>
              <StepHeader num={6} title="Repair Loop" status={latestValidation?.allOk ? 'pass' : result.validation.allOk ? null : 'fail'} />

              {result.validation.allOk ? (
                <p className="text-sm text-emerald-400">✓ No repair needed — first attempt passed!</p>
              ) : (
                <>
                  <p className="text-xs text-slate-400 mb-4">
                    We feed the exact error messages back to Gemini: <em>"Here are your mistakes — fix them."</em><br/>
                    This implements the Phase 4 validator + repair architecture. Max 3 cycles.
                  </p>

                  {/* Repair history */}
                  {repairs.map((r, i) => (
                    <div key={i} className="mb-4 border border-slate-700 rounded-lg overflow-hidden">
                      <div className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 ${r.validation.allOk ? 'bg-emerald-900/40 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                        <span>Repair Cycle {r.cycle} / 3</span>
                        {r.validation.allOk
                          ? <span className="ml-auto text-emerald-300">✓ FIXED</span>
                          : <span className="ml-auto text-red-400">✗ Still {r.validation.errors.length} error(s)</span>}
                      </div>
                      <div className="p-3">
                        <p className="text-xs text-slate-500 mb-1">Gemini's repaired IR:</p>
                        <CodeBlock code={r.ir} maxH="240px" />
                        <div className="mt-2">
                          <ValidationPanel v={r.validation} />
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Repair button */}
                  {canRepair && (
                    <button
                      onClick={handleRepair}
                      disabled={isRepairing}
                      className="px-5 py-2.5 rounded-lg font-semibold text-sm bg-orange-600 hover:bg-orange-500 disabled:opacity-40 transition-colors"
                    >
                      {isRepairing
                        ? '⏳  Repairing...'
                        : `🔧  Try Repair  (Cycle ${repairs.length + 1} / 3)`}
                    </button>
                  )}

                  {repairs.length >= 3 && !latestValidation?.allOk && (
                    <p className="text-sm text-slate-400 mt-2">
                      Max repair cycles reached. This construct is too complex for Gemini to self-correct.<br/>
                      <span className="text-xs">Try Variant B or C for better results on complex control flow.</span>
                    </p>
                  )}
                </>
              )}
            </Card>

            {/* Final summary bar */}
            <div className={`sticky bottom-0 left-0 right-0 p-3 rounded-xl text-sm font-semibold text-center ${
              latestValidation?.allOk
                ? 'bg-emerald-900 border border-emerald-700 text-emerald-200'
                : 'bg-red-900/80 border border-red-700 text-red-200'
            }`}>
              {latestValidation?.allOk
                ? `✓  PASSED${repairs.length > 0 ? ` after ${repairs.length} repair cycle(s)` : ' on first attempt'}  —  ${selected ? selected.label : 'Custom'}, Variant ${variant}`
                : `✗  Still failing after ${repairs.length} repair cycle(s)  —  ${selected ? selected.label : 'Custom'}, Variant ${variant}  |  Try Variant B or C`
              }
            </div>
          </>
        )}
      </main>
    </div>
  )
}
