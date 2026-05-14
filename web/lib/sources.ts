import fs from 'fs'
import path from 'path'

// The Next.js app lives in web/, so project root is one level up
const ROOT = path.join(process.cwd(), '..')

export const CONSTRUCTS = [
  { id: '01', name: 'var_decl',    label: 'Variable Declarations', difficulty: 'Easy',   hint: 'No control flow. Gemini almost always passes.' },
  { id: '02', name: 'expressions', label: 'Expressions',           difficulty: 'Easy',   hint: 'Arithmetic ops. Straight-line code.' },
  { id: '03', name: 'if_else',     label: 'If / Else Branch',      difficulty: 'Medium', hint: 'Needs phi node at merge block.' },
  { id: '04', name: 'while_loop',  label: 'While Loop',            difficulty: 'Medium', hint: 'Phi nodes at loop header for loop vars.' },
  { id: '05', name: 'for_loop',    label: 'For Loop',              difficulty: 'Medium', hint: 'Desugared to while. Same phi requirements.' },
  { id: '06', name: 'functions',   label: 'Functions',             difficulty: 'Medium', hint: 'define, call, ret, parameter types.' },
  { id: '07', name: 'nested_ctrl', label: 'Nested If in While',    difficulty: 'Hard',   hint: 'Two-level phi nodes. Hardest case.' },
]

export function getSourceCode(id: string, name: string): string {
  const p = path.join(ROOT, 'phase1', 'src_programs', `${id}_${name}.src`)
  return fs.readFileSync(p, 'utf-8')
}

export function getGroundTruth(id: string, name: string): string | null {
  const p = path.join(ROOT, 'phase1', 'ground_truth', `${id}_${name}.gt.ll`)
  if (!fs.existsSync(p)) return null
  return fs.readFileSync(p, 'utf-8')
}

export function getApiKey(): string {
  if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY
  // Fall back to reading parent project's .env directly
  const envPath = path.join(ROOT, 'phase2', '.env')
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8')
    const match = content.match(/^GEMINI_API_KEY=(.+)$/m)
    if (match) return match[1].trim()
  }
  throw new Error('GEMINI_API_KEY not found. Add it to phase2/.env')
}
