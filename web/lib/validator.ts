// TypeScript port of tools/validate.py

export interface Diagnostic {
  stage: number
  severity: 'ERROR' | 'WARNING'
  lineNo: number
  message: string
}

interface Instruction {
  lineNo: number
  raw: string
  result?: string
  resultType?: string
  opcode?: string
  operands: string[]
  isTerminator: boolean
}

interface BasicBlock {
  label: string
  instructions: Instruction[]
  predecessors: string[]
  successors: string[]
  hasTerminator: boolean
}

interface IRFunction {
  name: string
  returnType: string
  blocks: Map<string, BasicBlock>
  entry?: string
}

export interface ValidationResult {
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

const KNOWN_OPCODES = new Set([
  'add', 'sub', 'mul', 'sdiv', 'udiv',
  'and', 'or', 'xor',
  'icmp', 'fcmp',
  'alloca', 'load', 'store',
  'br', 'ret', 'call', 'phi',
  'zext', 'sext', 'trunc', 'bitcast', 'getelementptr',
])

function normalize(line: string): string {
  return line
    .replace(/\b(nsw|nuw|exact|inbounds|volatile|atomic|nnan|ninf|afn|reassoc|arcp|contract|fast)\b\s*/g, '')
    .replace(/,\s*align\s+\d+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function parseInstruction(line: string, lineNo: number, diags: Diagnostic[]): Instruction | null {
  const instr: Instruction = { lineNo, raw: line, operands: [], isTerminator: false }
  const norm = normalize(line)

  const assignMatch = norm.match(/^(%[\w.]+)\s*=\s*(\w+)\s*(.*)/)
  if (assignMatch) {
    instr.result = assignMatch[1]
    instr.opcode = assignMatch[2]
    instr.operands = assignMatch[3].split(/\s+/).filter(Boolean)
    if (!KNOWN_OPCODES.has(instr.opcode)) {
      diags.push({ stage: 1, severity: 'ERROR', lineNo, message: `Unknown opcode '${instr.opcode}'.` })
    }
    if (instr.opcode === 'icmp') instr.resultType = 'i1'
    else if (['add', 'sub', 'mul', 'sdiv'].includes(instr.opcode)) {
      instr.resultType = instr.operands[0]?.replace(',', '')
    } else if (instr.opcode === 'load') {
      instr.resultType = instr.operands[0]?.replace(',', '')
    }
    return instr
  }

  const termMatch = norm.match(/^(ret|br)\s*(.*)/)
  if (termMatch) {
    instr.opcode = termMatch[1]
    instr.operands = termMatch[2].split(/\s+/).filter(Boolean)
    instr.isTerminator = true
    return instr
  }

  if (norm.match(/^store\s/)) { instr.opcode = 'store'; return instr }
  if (norm.match(/^call\s/))  { instr.opcode = 'call';  return instr }

  diags.push({ stage: 1, severity: 'WARNING', lineNo, message: `Could not parse: '${line.slice(0, 60)}'` })
  return null
}

function stage1(lines: string[]): [Diagnostic[], IRFunction[]] {
  const diags: Diagnostic[] = []
  const functions: IRFunction[] = []
  let currentFunc: IRFunction | null = null
  let currentBlock: BasicBlock | null = null
  let inFunction = false

  lines.forEach((rawLine, idx) => {
    const lineNo = idx + 1
    const line = rawLine.trim()
    if (!line || line.startsWith(';')) return

    const funcMatch = line.match(/define\s+(\S+)\s+@(\w+)\s*\(.*\)\s*\{?/)
    if (funcMatch) {
      currentFunc = { name: funcMatch[2], returnType: funcMatch[1], blocks: new Map() }
      functions.push(currentFunc)
      inFunction = true
      currentBlock = null
      return
    }

    if (line === '}' && inFunction) {
      inFunction = false; currentFunc = null; currentBlock = null; return
    }
    if (!inFunction || !currentFunc) return

    const labelMatch = line.match(/^(\w[\w.]*)\s*:/)
    if (labelMatch) {
      const label = labelMatch[1]
      currentBlock = { label, instructions: [], predecessors: [], successors: [], hasTerminator: false }
      if (!currentFunc.entry) currentFunc.entry = label
      currentFunc.blocks.set(label, currentBlock)
      return
    }

    if (!currentBlock) {
      currentBlock = { label: 'entry', instructions: [], predecessors: [], successors: [], hasTerminator: false }
      currentFunc.entry = 'entry'
      currentFunc.blocks.set('entry', currentBlock)
    }

    const instr = parseInstruction(line, lineNo, diags)
    if (instr) {
      currentBlock.instructions.push(instr)
      if (instr.isTerminator) currentBlock.hasTerminator = true
    }
  })

  for (const func of functions) {
    for (const [label, block] of func.blocks) {
      if (!block.hasTerminator) {
        diags.push({
          stage: 1, severity: 'ERROR', lineNo: 0,
          message: `Block '%${label}' in @${func.name} has no terminator (expected ret or br).`
        })
      }
    }
  }
  return [diags, functions]
}

function stage2(functions: IRFunction[]): Diagnostic[] {
  const diags: Diagnostic[] = []
  for (const func of functions) {
    const defined = new Map<string, [string | undefined, string, number]>()
    for (const [label, block] of func.blocks) {
      for (const instr of block.instructions) {
        if (instr.result) {
          if (defined.has(instr.result)) {
            const prev = defined.get(instr.result)!
            diags.push({ stage: 2, severity: 'ERROR', lineNo: instr.lineNo,
              message: `SSA violation: '${instr.result}' defined more than once. First in '%${prev[1]}' at line ${prev[2]}.` })
          } else {
            defined.set(instr.result, [instr.resultType, label, instr.lineNo])
          }
        }
      }
    }
    for (const [label, block] of func.blocks) {
      for (const instr of block.instructions) {
        if (instr.opcode === 'br' && instr.operands.length > 0) {
          if (instr.operands[0] === 'i32') {
            diags.push({ stage: 2, severity: 'ERROR', lineNo: instr.lineNo,
              message: `Type mismatch in '%${label}': br condition is i32, must be i1. Use icmp first.` })
          }
          const condReg = instr.operands.find((op: string) => op.startsWith('%'))
          if (condReg && defined.has(condReg)) {
            const cType = defined.get(condReg)![0]
            if (cType && cType !== 'i1') {
              diags.push({ stage: 2, severity: 'ERROR', lineNo: instr.lineNo,
                message: `Branch condition '${condReg}' has type '${cType}', must be i1.` })
            }
          }
        }
      }
    }
  }
  return diags
}

function stage3(functions: IRFunction[]): Diagnostic[] {
  const diags: Diagnostic[] = []
  for (const func of functions) {
    const allLabels = new Set(func.blocks.keys())
    for (const [label, block] of func.blocks) {
      for (const instr of block.instructions) {
        if (instr.opcode === 'br') {
          const targets = [...instr.raw.matchAll(/label\s+%?(\w[\w.]*)/g)].map(m => m[1])
          for (const target of targets) {
            if (!allLabels.has(target)) {
              diags.push({ stage: 3, severity: 'ERROR', lineNo: instr.lineNo,
                message: `Branch target '%${target}' in '%${label}' does not exist in @${func.name}.` })
            } else {
              block.successors.push(target)
              func.blocks.get(target)!.predecessors.push(label)
            }
          }
        }
      }
    }
    if (func.entry) {
      const visited = new Set<string>()
      const queue = [func.entry]
      while (queue.length > 0) {
        const node = queue.shift()!
        if (visited.has(node)) continue
        visited.add(node)
        for (const s of func.blocks.get(node)?.successors ?? []) {
          if (!visited.has(s)) queue.push(s)
        }
      }
      for (const label of allLabels) {
        if (!visited.has(label)) {
          diags.push({ stage: 3, severity: 'WARNING', lineNo: 0,
            message: `Block '%${label}' in @${func.name} is unreachable from entry.` })
        }
      }
    }
    for (const [label, block] of func.blocks) {
      const hasRet = block.instructions.some(i => i.opcode === 'ret')
      if (block.hasTerminator && !hasRet && block.successors.length === 0 && block.instructions.some((i: Instruction) => i.isTerminator)) {
        diags.push({ stage: 3, severity: 'ERROR', lineNo: 0,
          message: `Block '%${label}' in @${func.name} has no successors and no ret (dead end).` })
      }
    }
  }
  return diags
}

export function validateIR(irText: string): ValidationResult {
  const lines = irText.split('\n')
  const [s1Diags, functions] = stage1(lines)
  const s1Errors = s1Diags.filter(d => d.severity === 'ERROR')
  const s1Warns  = s1Diags.filter(d => d.severity === 'WARNING')

  const result: ValidationResult = {
    parseOk: s1Errors.length === 0,
    ssaOk: false, cfOk: false, allOk: false,
    errors:   s1Errors.map(d => `[S${d.stage} ERROR] Line ${d.lineNo}: ${d.message}`),
    warnings: s1Warns.map( d => `[S${d.stage} WARN]  Line ${d.lineNo}: ${d.message}`),
    stage1Errors: s1Errors, stage2Errors: [], stage3Errors: [],
  }
  if (s1Errors.length > 0) return result

  const s2Diags  = stage2(functions)
  const s2Errors = s2Diags.filter(d => d.severity === 'ERROR')
  result.ssaOk = s2Errors.length === 0
  result.stage2Errors = s2Errors
  result.errors.push(...s2Errors.map(d => `[S${d.stage} ERROR] Line ${d.lineNo}: ${d.message}`))

  const s3Diags  = stage3(functions)
  const s3Errors = s3Diags.filter(d => d.severity === 'ERROR')
  const s3Warns  = s3Diags.filter(d => d.severity === 'WARNING')
  result.cfOk  = s3Errors.length === 0
  result.allOk = result.ssaOk && result.cfOk
  result.stage3Errors = s3Errors
  result.errors.push(  ...s3Errors.map(d => `[S${d.stage} ERROR] Line ${d.lineNo}: ${d.message}`))
  result.warnings.push(...s3Warns.map( d => `[S${d.stage} WARN]  Line ${d.lineNo}: ${d.message}`))
  return result
}
