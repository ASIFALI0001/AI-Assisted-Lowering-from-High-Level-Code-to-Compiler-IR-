import { NextRequest, NextResponse } from 'next/server'
import { GoogleGenerativeAI } from '@google/generative-ai'
import { getSourceCode, getGroundTruth, getApiKey } from '@/lib/sources'
import { buildPrompt, Variant } from '@/lib/prompts'
import { validateIR } from '@/lib/validator'

const MODEL = 'gemini-2.5-flash'

function extractIR(raw: string): string {
  const m = raw.match(/```(?:llvm|ll)?\s*\n([\s\S]*?)```/)
  return m ? m[1].trim() : raw.trim()
}

function compareWithGT(gtText: string, irText: string) {
  const blockRx = /^(\w[\w.]*)\s*:/gm
  const gtBlocks  = Array.from(new Set(Array.from(gtText.matchAll(blockRx)).map(m => m[1])))
  const llmBlocks = Array.from(new Set(Array.from(irText.matchAll(blockRx)).map(m => m[1])))
  const gtPhis  = (gtText.match(/=\s*phi\b/g)  || []).length
  const llmPhis = (irText.match(/=\s*phi\b/g) || []).length
  const gtFns   = Array.from(gtText.matchAll(/define\s+\S+\s+@(\w+)/g)).map(m => m[1])
  const llmFns  = Array.from(irText.matchAll(/define\s+\S+\s+@(\w+)/g)).map(m => m[1])
  const gtSet   = new Set(gtBlocks)
  const llmSet  = new Set(llmBlocks)
  return {
    gtText,
    blockMatch:    gtBlocks.every(b => llmSet.has(b)) && llmBlocks.every(b => gtSet.has(b)),
    missingBlocks: gtBlocks.filter(b => !llmSet.has(b)),
    extraBlocks:   llmBlocks.filter(b => !gtSet.has(b)),
    phiMatch:  gtPhis === llmPhis,
    gtPhis, llmPhis,
    fnMatch:   JSON.stringify(gtFns.sort()) === JSON.stringify(llmFns.sort()),
    gtFns, llmFns,
  }
}

export async function POST(req: NextRequest) {
  try {
    const { constructId, constructName, variant, customCode } = await req.json()

    const apiKey = getApiKey()
    const source = customCode?.trim() || getSourceCode(constructId, constructName)
    const prompt = buildPrompt(source, variant as Variant)

    const genAI = new GoogleGenerativeAI(apiKey)
    const model = genAI.getGenerativeModel({ model: MODEL })
    const res = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: 4096, temperature: 0.7 },
    })
    const rawOutput = res.response.text()
    const ir = extractIR(rawOutput)
    const validation = validateIR(ir)
    const gt = (!customCode && constructId) ? getGroundTruth(constructId, constructName) : null
    const comparison = gt ? compareWithGT(gt, ir) : null

    return NextResponse.json({ source, prompt, rawOutput, ir, validation, comparison })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
