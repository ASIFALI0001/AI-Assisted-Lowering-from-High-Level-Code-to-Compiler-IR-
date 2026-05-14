import { NextRequest, NextResponse } from 'next/server'
import { GoogleGenerativeAI } from '@google/generative-ai'
import { getApiKey } from '@/lib/sources'
import { buildRepairPrompt } from '@/lib/prompts'
import { validateIR } from '@/lib/validator'

const MODEL = 'gemini-2.5-flash'

function extractIR(raw: string): string {
  const m = raw.match(/```(?:llvm|ll)?\s*\n([\s\S]*?)```/)
  return m ? m[1].trim() : raw.trim()
}

export async function POST(req: NextRequest) {
  try {
    const { source, ir, errors } = await req.json()
    const apiKey = getApiKey()
    const prompt = buildRepairPrompt(source, ir, errors)

    const genAI = new GoogleGenerativeAI(apiKey)
    const model = genAI.getGenerativeModel({ model: MODEL })
    const res = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: 4096, temperature: 0.7 },
    })
    const rawOutput = res.response.text()
    const newIR = extractIR(rawOutput)
    const validation = validateIR(newIR)

    return NextResponse.json({ rawOutput, ir: newIR, validation })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
