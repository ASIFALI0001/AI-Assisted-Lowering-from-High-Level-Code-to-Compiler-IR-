'use client'

import { useState } from 'react'

type Variant = 'A' | 'B' | 'C'
type View = 'dashboard' | 'lab'

interface Diagnostic {
  stage: number
  severity: string
  lineNo: number
  message: string
}

interface ValidationResult {
  parseOk: boolean
  ssaOk: boolean
  cfOk: boolean
  allOk: boolean
  errors: string[]
  warnings: string[]
  stage1Errors: Diagnostic[]
  stage2Errors: Diagnostic[]
  stage3Errors: Diagnostic[]
}

interface ComparisonResult {
  gtText: string
  blockMatch: boolean
  missingBlocks: string[]
  extraBlocks: string[]
  phiMatch: boolean
  gtPhis: number
  llmPhis: number
  fnMatch: boolean
  gtFns: string[]
  llmFns: string[]
}

interface PipelineResult {
  source: string
  prompt: string
  rawOutput: string
  ir: string
  validation: ValidationResult
  comparison: ComparisonResult | null
}

interface RepairAttempt {
  cycle: number
  ir: string
  validation: ValidationResult
}

const CONSTRUCTS = [
  { id: '01', name: 'var_decl', label: 'Variable Declarations', difficulty: 'Easy', tone: 'success' },
  { id: '02', name: 'expressions', label: 'Expressions', difficulty: 'Easy', tone: 'success' },
  { id: '03', name: 'if_else', label: 'If / Else Branch', difficulty: 'Medium', tone: 'warning' },
  { id: '04', name: 'while_loop', label: 'While Loop', difficulty: 'Medium', tone: 'warning' },
  { id: '05', name: 'for_loop', label: 'For Loop', difficulty: 'Medium', tone: 'warning' },
  { id: '06', name: 'functions', label: 'Functions', difficulty: 'Medium', tone: 'warning' },
  { id: '07', name: 'nested_ctrl', label: 'Nested Control Flow', difficulty: 'Hard', tone: 'danger' },
]

const VARIANT_INFO = {
  A: { label: 'Minimal', desc: 'A plain translation request with no extra compiler rules.' },
  B: { label: 'Rule Injected', desc: 'The prompt includes explicit LLVM IR constraints.' },
  C: { label: 'Few Shot', desc: 'Rules plus a worked if/else example for guidance.' },
}

const PIPELINE_STEPS = [
  'Load source program',
  'Build prompt variant',
  'Call Gemini 2.5 Flash',
  'Extract LLVM IR',
  'Validate syntax, SSA, and CFG',
  'Compare with ground truth',
  'Repair with validator feedback',
]

const PROJECT_PHASES = [
  { name: 'Phase 1', title: 'Dataset', detail: 'Seven small C-like source programs with hand-written LLVM IR ground truth.' },
  { name: 'Phase 2', title: 'Generation', detail: 'Gemini is called across three prompt variants and three runs per construct.' },
  { name: 'Phase 3', title: 'Analysis', detail: 'JSON logs are converted into failure categories, pass rates, CSV, and report notes.' },
  { name: 'Phase 4', title: 'Repair Loop', detail: 'Validator diagnostics are sent back to the model to attempt self-correction.' },
  { name: 'Phase 5', title: 'Report', detail: 'The final write-up explains methodology, failures, limitations, and future work.' },
]

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ')
}

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={cx('surface-panel', className)}>{children}</section>
}

function CodeBlock({ code, maxH = '400px' }: { code: string; maxH?: string }) {
  return (
    <pre className="code-block overflow-auto rounded-md border border-slate-800 bg-slate-950/90 p-4 text-slate-200" style={{ maxHeight: maxH }}>
      {code}
    </pre>
  )
}

function StatusBadge({ status }: { status: 'pass' | 'fail' | 'pending' }) {
  const label = status === 'pass' ? 'PASS' : status === 'fail' ? 'FAIL' : 'PENDING'
  return (
    <span
      className={cx(
        'inline-flex h-6 items-center rounded-full px-2.5 text-xs font-semibold',
        status === 'pass' && 'bg-emerald-500/12 text-emerald-700 ring-1 ring-emerald-500/20',
        status === 'fail' && 'bg-rose-500/12 text-rose-700 ring-1 ring-rose-500/20',
        status === 'pending' && 'bg-slate-500/10 text-slate-500 ring-1 ring-slate-300'
      )}
    >
      {label}
    </span>
  )
}

function StepHeader({ num, title, status }: { num: number; title: string; status?: 'pass' | 'fail' | null }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-900 text-sm font-bold text-white">
        {num}
      </span>
      <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-600">{title}</h2>
      {status && <StatusBadge status={status} />}
    </div>
  )
}

function StageRow({ label, ok, skipped, errors }: { label: string; ok: boolean; skipped?: boolean; errors: Diagnostic[] }) {
  const status = skipped ? 'pending' : ok ? 'pass' : 'fail'

  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="flex items-center gap-3">
        <span
          className={cx(
            'flex h-7 w-7 items-center justify-center rounded-md text-sm font-bold',
            status === 'pass' && 'bg-emerald-50 text-emerald-700',
            status === 'fail' && 'bg-rose-50 text-rose-700',
            status === 'pending' && 'bg-slate-100 text-slate-500'
          )}
        >
          {status === 'pass' ? 'OK' : status === 'fail' ? '!' : '-'}
        </span>
        <span className="flex-1 text-sm font-medium text-slate-700">{label}</span>
        <StatusBadge status={status} />
      </div>
      {!ok && !skipped && errors.map((e, i) => (
        <div key={`${e.stage}-${e.lineNo}-${i}`} className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 font-mono text-xs text-rose-800">
          {e.message}
        </div>
      ))}
    </div>
  )
}

function ValidationPanel({ v }: { v: ValidationResult }) {
  return (
    <div className="space-y-3">
      <StageRow label="Stage 1: Syntax check" ok={v.parseOk} errors={v.stage1Errors} />
      <StageRow label="Stage 2: SSA and type check" ok={v.ssaOk} skipped={!v.parseOk} errors={v.stage2Errors} />
      <StageRow label="Stage 3: Control-flow graph" ok={v.cfOk} skipped={!v.parseOk} errors={v.stage3Errors} />
      <div className={cx('rounded-md border px-4 py-3 text-sm font-semibold', v.allOk ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-rose-200 bg-rose-50 text-rose-800')}>
        {v.allOk ? 'All validation stages passed. The IR is structurally valid.' : `Failed with ${v.errors.length} error(s). Review the diagnostics above.`}
      </div>
      {v.warnings.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 font-mono text-xs text-amber-800">
          {v.warnings.length} warning(s): {v.warnings[0]}
        </div>
      )}
    </div>
  )
}

function ComparisonPanel({ c }: { c: ComparisonResult }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCheck label="Functions" ok={c.fnMatch} value={c.llmFns.join(', ') || 'none'} />
        <MetricCheck label="Blocks" ok={c.blockMatch} value={c.blockMatch ? 'match' : `missing ${c.missingBlocks.length}`} />
        <MetricCheck label="Phi nodes" ok={c.phiMatch} value={`${c.llmPhis} / ${c.gtPhis}`} />
      </div>
      {!c.phiMatch && c.llmPhis < c.gtPhis && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Missing phi nodes are a common failure mode when lowering branching and loop state into SSA form.
        </div>
      )}
      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-slate-600 transition hover:text-slate-950">
          Show ground truth IR
        </summary>
        <div className="mt-3">
          <CodeBlock code={c.gtText} maxH="280px" />
        </div>
      </details>
    </div>
  )
}

function MetricCheck({ label, ok, value }: { label: string; ok: boolean; value: string }) {
  return (
    <div className={cx('rounded-md border p-3', ok ? 'border-emerald-200 bg-emerald-50' : 'border-rose-200 bg-rose-50')}>
      <div className={cx('text-xs font-semibold uppercase tracking-[0.14em]', ok ? 'text-emerald-700' : 'text-rose-700')}>
        {ok ? 'Matched' : 'Mismatch'}
      </div>
      <div className="mt-1 text-sm font-semibold text-slate-900">{label}</div>
      <div className="mt-1 text-xs text-slate-600">{value}</div>
    </div>
  )
}

function DashboardView({ onOpenLab }: { onOpenLab: () => void }) {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-5 py-6 lg:px-8">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">Compiler Design Assignment 15</p>
          <h1>LLM Compiler Lowering</h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            This project tests whether Gemini 2.5 Flash can translate a constrained C-like source language into structurally valid LLVM IR, then measures where the generated IR breaks and whether validator feedback can repair it.
          </p>
        </div>
        <button onClick={onOpenLab} className="primary-action">
          Open pipeline lab
        </button>
      </section>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard value="7" label="source constructs" detail="Declarations, expressions, branches, loops, functions, and nested control flow." />
        <StatCard value="63" label="LLM generations" detail="Three prompt variants, three runs each, across every construct." />
        <StatCard value="3" label="validator stages" detail="Syntax, SSA/type discipline, and control-flow graph checks." />
        <StatCard value="3x" label="repair budget" detail="The demo can send diagnostics back to Gemini for up to three repair cycles." />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel>
          <div className="section-heading">
            <p className="eyebrow">Research Question</p>
            <h2>Can an LLM behave like a tiny compiler backend?</h2>
          </div>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            The experiment focuses on lowering source constructs into LLVM IR patterns: stack slots for local variables, arithmetic and comparisons for expressions, branches and merge blocks for conditionals, loop headers and back edges for iteration, function definitions and calls, and phi nodes where SSA values merge.
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {CONSTRUCTS.map((construct) => (
              <div key={construct.id} className="construct-card">
                <span className="font-mono text-xs text-slate-500">{construct.id}</span>
                <span className="font-semibold text-slate-900">{construct.label}</span>
                <span className={cx('difficulty-pill', construct.tone === 'success' && 'tone-success', construct.tone === 'warning' && 'tone-warning', construct.tone === 'danger' && 'tone-danger')}>
                  {construct.difficulty}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="section-heading">
            <p className="eyebrow">Prompt Variants</p>
            <h2>Same task, different guidance</h2>
          </div>
          <div className="mt-5 space-y-3">
            {(['A', 'B', 'C'] as Variant[]).map((variant) => (
              <div key={variant} className="prompt-row">
                <span>{variant}</span>
                <div>
                  <h3>{VARIANT_INFO[variant].label}</h3>
                  <p>{VARIANT_INFO[variant].desc}</p>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel>
          <div className="section-heading">
            <p className="eyebrow">Pipeline</p>
            <h2>From source to repaired IR</h2>
          </div>
          <ol className="mt-5 space-y-3">
            {PIPELINE_STEPS.map((step, index) => (
              <li key={step} className="pipeline-row">
                <span>{index + 1}</span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel>
          <div className="section-heading">
            <p className="eyebrow">Project Phases</p>
            <h2>What each folder contributes</h2>
          </div>
          <div className="mt-5 space-y-4">
            {PROJECT_PHASES.map((phase) => (
              <div key={phase.name} className="phase-row">
                <div>
                  <span>{phase.name}</span>
                  <h3>{phase.title}</h3>
                </div>
                <p>{phase.detail}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel className="mb-8">
        <div className="section-heading">
          <p className="eyebrow">Important Context</p>
          <h2>What the dashboard is telling you</h2>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <InfoBlock title="No LLVM toolchain required" body="The validator is written in Python and checks the subset of IR this assignment cares about." />
          <InfoBlock title="Failures are categorized" body="The analysis phase turns saved JSON logs into pass/fail statistics and failure notes." />
          <InfoBlock title="Repair is the Phase 4 idea" body="The interactive demo shows a partial implementation of a validator-driven repair loop." />
        </div>
      </Panel>
    </div>
  )
}

function StatCard({ value, label, detail }: { value: string; label: string; detail: string }) {
  return (
    <Panel className="min-h-[150px]">
      <div className="text-3xl font-bold tracking-tight text-slate-950">{value}</div>
      <div className="mt-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{detail}</p>
    </Panel>
  )
}

function InfoBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  )
}

export default function Home() {
  const [view, setView] = useState<View>('dashboard')
  const [selectedIdx, setSelectedIdx] = useState<number | null>(0)
  const [useCustom, setUseCustom] = useState(false)
  const [customCode, setCustomCode] = useState(`func max_val(a: int, b: int) -> int {\n  int result = 0;\n  if (a > b) {\n    result = a;\n  } else {\n    result = b;\n  }\n  return result;\n}`)
  const [variant, setVariant] = useState<Variant>('A')
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [repairs, setRepairs] = useState<RepairAttempt[]>([])
  const [isRepairing, setIsRepairing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selected = selectedIdx !== null ? CONSTRUCTS[selectedIdx] : null
  const latestValidation = repairs.length > 0 ? repairs[repairs.length - 1].validation : result?.validation
  const canRepair = result && !latestValidation?.allOk && repairs.length < 3

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
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
        return
      }
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
    setError(null)

    try {
      const res = await fetch('/api/repair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: result.source, ir: currentIR, errors: currentErrors }),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
        return
      }
      setRepairs(prev => [...prev, { cycle: prev.length + 1, ir: data.ir, validation: data.validation }])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIsRepairing(false)
    }
  }

  return (
    <div className="min-h-dvh bg-[var(--app-bg)] text-slate-900">
      <aside className="app-sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">IR</div>
          <div>
            <h1>LLM Compiler Lowering</h1>
            <p>Gemini to LLVM IR research demo</p>
          </div>
        </div>

        <nav className="nav-switch" aria-label="Primary">
          <button onClick={() => setView('dashboard')} className={cx(view === 'dashboard' && 'active')}>
            Dashboard
          </button>
          <button onClick={() => setView('lab')} className={cx(view === 'lab' && 'active')}>
            Pipeline Lab
          </button>
        </nav>

        <div className="sidebar-section">
          <p className="sidebar-label">Program</p>
          <div className="space-y-1">
            {CONSTRUCTS.map((c, i) => (
              <button
                key={c.id}
                onClick={() => {
                  setSelectedIdx(i)
                  setUseCustom(false)
                  setResult(null)
                  setRepairs([])
                  setView('lab')
                }}
                className={cx('sidebar-option', !useCustom && selectedIdx === i && 'selected')}
              >
                <span className="font-mono text-xs text-slate-400">{c.id}</span>
                <span>{c.label}</span>
                <span className={cx('ml-auto difficulty-pill', c.tone === 'success' && 'tone-success', c.tone === 'warning' && 'tone-warning', c.tone === 'danger' && 'tone-danger')}>
                  {c.difficulty}
                </span>
              </button>
            ))}
            <button
              onClick={() => {
                setUseCustom(true)
                setSelectedIdx(null)
                setResult(null)
                setRepairs([])
                setView('lab')
              }}
              className={cx('sidebar-option', useCustom && 'selected')}
            >
              <span className="font-mono text-xs text-slate-400">++</span>
              <span>Custom Code</span>
            </button>
          </div>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-label">Prompt Style</p>
          <div className="variant-group">
            {(['A', 'B', 'C'] as Variant[]).map(v => (
              <button key={v} onClick={() => setVariant(v)} className={cx(variant === v && 'selected')}>
                {v}
              </button>
            ))}
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-500">{VARIANT_INFO[variant].desc}</p>
        </div>

        <button
          onClick={() => {
            setView('lab')
            handleRun()
          }}
          disabled={isRunning || (!useCustom && selectedIdx === null)}
          className="run-button"
        >
          {isRunning ? 'Calling Gemini...' : 'Run pipeline'}
        </button>

        {error && (
          <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {error}
          </div>
        )}
      </aside>

      <main className="lg:pl-[320px]">
        {view === 'dashboard' ? (
          <DashboardView onOpenLab={() => setView('lab')} />
        ) : (
          <div className="mx-auto max-w-6xl space-y-5 px-5 py-6 lg:px-8">
            <div className="lab-header">
              <div>
                <p className="eyebrow">Interactive Demo</p>
                <h1>Pipeline Lab</h1>
                <p>Run a source construct through Gemini, validate the generated LLVM IR, compare it with ground truth, then try the repair loop.</p>
              </div>
            </div>

            {useCustom && (
              <Panel>
                <StepHeader num={0} title="Custom Program" />
                <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="custom-code">
                  Source code
                </label>
                <textarea
                  id="custom-code"
                  value={customCode}
                  onChange={e => setCustomCode(e.target.value)}
                  className="code-block min-h-52 w-full resize-y rounded-md border border-slate-300 bg-white p-4 text-slate-900 outline-none transition focus:border-slate-900 focus:ring-4 focus:ring-slate-200"
                  spellCheck={false}
                />
              </Panel>
            )}

            {!result && !isRunning && (
              <Panel className="empty-state">
                <p className="eyebrow">Ready</p>
                <h2>Choose a construct and run the pipeline.</h2>
                <p>The generated prompt, LLVM IR, validation report, comparison, and repair controls will appear here.</p>
              </Panel>
            )}

            {isRunning && (
              <Panel className="empty-state">
                <div className="loader" />
                <h2>Calling Gemini API</h2>
                <p>The lab is generating LLVM IR for the selected source program.</p>
              </Panel>
            )}

            {result && (
              <>
                <Panel>
                  <StepHeader num={1} title="Source Code" />
                  <p className="mb-3 text-sm text-slate-600">The C-like program sent through the lowering pipeline.</p>
                  <CodeBlock code={result.source} />
                </Panel>

                <Panel>
                  <StepHeader num={2} title={`Prompt Sent to Gemini: Variant ${variant}`} />
                  <p className="mb-3 text-sm text-slate-600">{VARIANT_INFO[variant].desc}</p>
                  <details>
                    <summary className="cursor-pointer text-sm font-medium text-slate-700 transition hover:text-slate-950">Show full prompt</summary>
                    <div className="mt-3">
                      <CodeBlock code={result.prompt} maxH="280px" />
                    </div>
                  </details>
                </Panel>

                <Panel>
                  <StepHeader num={3} title="Generated LLVM IR" />
                  <p className="mb-3 text-sm text-slate-600">The model output after extraction and cleanup.</p>
                  <CodeBlock code={result.ir} />
                </Panel>

                <Panel>
                  <StepHeader num={4} title="Validator Results" status={result.validation.allOk ? 'pass' : 'fail'} />
                  <p className="mb-4 text-sm text-slate-600">Three structural checks: syntax, SSA/type discipline, and control flow.</p>
                  <ValidationPanel v={result.validation} />
                </Panel>

                {result.comparison && (
                  <Panel>
                    <StepHeader num={5} title="Ground Truth Comparison" />
                    <p className="mb-4 text-sm text-slate-600">A structural comparison against the hand-written correct LLVM IR.</p>
                    <ComparisonPanel c={result.comparison} />
                  </Panel>
                )}

                <Panel>
                  <StepHeader num={6} title="Repair Loop" status={latestValidation?.allOk ? 'pass' : result.validation.allOk ? null : 'fail'} />

                  {result.validation.allOk ? (
                    <p className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                      No repair needed. The first attempt passed validation.
                    </p>
                  ) : (
                    <>
                      <p className="mb-4 text-sm leading-6 text-slate-600">
                        The repair loop sends the current IR and exact validator diagnostics back to Gemini. It can try up to three correction cycles.
                      </p>

                      {repairs.map((r) => (
                        <div key={r.cycle} className="mb-4 overflow-hidden rounded-md border border-slate-200 bg-slate-50">
                          <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
                            <span className="text-sm font-semibold text-slate-900">Repair cycle {r.cycle} / 3</span>
                            <span className="ml-auto">
                              <StatusBadge status={r.validation.allOk ? 'pass' : 'fail'} />
                            </span>
                          </div>
                          <div className="space-y-4 p-4">
                            <CodeBlock code={r.ir} maxH="240px" />
                            <ValidationPanel v={r.validation} />
                          </div>
                        </div>
                      ))}

                      {canRepair && (
                        <button onClick={handleRepair} disabled={isRepairing} className="secondary-action">
                          {isRepairing ? 'Repairing...' : `Try repair cycle ${repairs.length + 1}`}
                        </button>
                      )}

                      {repairs.length >= 3 && !latestValidation?.allOk && (
                        <p className="mt-3 text-sm text-slate-600">
                          Maximum repair cycles reached. Try Variant B or C for more guidance on complex control flow.
                        </p>
                      )}
                    </>
                  )}
                </Panel>

                <div className={cx('result-banner', latestValidation?.allOk ? 'passed' : 'failed')}>
                  {latestValidation?.allOk
                    ? `Passed${repairs.length > 0 ? ` after ${repairs.length} repair cycle(s)` : ' on first attempt'}: ${selected ? selected.label : 'Custom'}, Variant ${variant}`
                    : `Still failing after ${repairs.length} repair cycle(s): ${selected ? selected.label : 'Custom'}, Variant ${variant}`}
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
