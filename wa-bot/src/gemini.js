// زنجیره مدل‌ها: اولویت با z.ai (GLM) است؛ اگر خطا داد، زنجیره Gemini اجرا می‌شود
// (هر مدل Gemini با retry؛ اگر به سقف سهمیه 429 یا شلوغی 503 خورد سراغ مدل بعدی می‌رویم)
const PRIMARY = process.env.GEMINI_MODEL || 'gemini-3.8-flash';
const FALLBACKS = (process.env.GEMINI_FALLBACK_MODELS || 'gemini-3.5-flash,gemini-3.5-flash-lite')
  .split(',').map(s => s.trim()).filter(Boolean);
const MODELS = [...new Set([PRIMARY, ...FALLBACKS])];
const API_KEY = process.env.GEMINI_API_KEY || '';

// z.ai (GLM) — مدل اولویت‌دار (پاسخ سریع‌تر)؛ Gemini به‌عنوان fallback
const ZAI_KEY = process.env.ZAI_API_KEY || '';
const ZAI_MODEL = process.env.ZAI_MODEL || 'glm-4.5-flash';
const ZAI_URL = 'https://api.z.ai/api/paas/v4/chat/completions';

async function callZai(systemPrompt, contents) {
  const messages = [{ role: 'system', content: systemPrompt }];
  for (const m of contents) {
    messages.push({ role: m.role === 'model' ? 'assistant' : 'user', content: m.parts[0].text });
  }
  const res = await fetch(ZAI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${ZAI_KEY}` },
    body: JSON.stringify({
      model: ZAI_MODEL,
      messages,
      max_tokens: 800,
      thinking: { type: 'disabled' }, // مدل reasoning است؛ بدون این، توکن‌ها صرف فکر می‌شود و خروجی خالی می‌ماند
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`z.ai ${res.status}: ${body.slice(0, 300)}`);
  }
  const data = await res.json();
  const text = (data.choices?.[0]?.message?.content || '').trim();
  if (!text) throw new Error('z.ai returned empty response');
  return text;
}

async function callModel(model, systemPrompt, contents) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': API_KEY },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: systemPrompt }] },
      contents,
      generationConfig: {
        temperature: 0.4,
        maxOutputTokens: 1536, // سقف ۵۱۲ را توکن‌های تفکر مدل مصرف می‌کرد و خروجی خالی می‌شد
      },
    }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    const err = new Error(`Gemini ${model} ${res.status}: ${body.slice(0, 300)}`);
    err.status = res.status;
    throw err;
  }

  const data = await res.json();
  // بخش‌های thought مدل هرگز نباید در متن پاسخ به کاربر بروند
  const parts = (data.candidates?.[0]?.content?.parts || []).filter(p => !p.thought);
  const text = parts.map(p => p.text || '').join('').trim();
  if (!text) {
    const err = new Error(`Gemini ${model} returned empty response`);
    err.retryable = true;
    throw err;
  }
  return text;
}

async function callGemini(systemPrompt, history, userText) {
  if (!API_KEY && !ZAI_KEY) throw new Error('no LLM API key is set');

  const contents = history.map(m => ({ role: m.role, parts: [{ text: m.text }] }));
  contents.push({ role: 'user', parts: [{ text: userText }] });

  // اولویت اول: z.ai — در صورت خطا سراغ زنجیره Gemini
  let lastErr = null;
  if (ZAI_KEY) {
    try {
      return await callZai(systemPrompt, contents);
    } catch (e) {
      lastErr = e;
      console.warn(`[gemini] z.ai failed (${e.message.slice(0, 120)}), falling back to gemini...`);
    }
  }

  for (const model of (API_KEY ? MODELS : [])) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        return await callModel(model, systemPrompt, contents);
      } catch (e) {
        lastErr = e;
        if (e.retryable || e.status === 429 || e.status >= 500) {
          if (attempt < 2) { await new Promise(r => setTimeout(r, 5000)); continue; }
          break; // سهمیه/خطای ماندگار این مدل — سراغ مدل بعدی
        }
        throw e; // خطای غیرقابل retry (مثل 400)
      }
    }
    console.warn(`[gemini] ${model} unavailable, trying next model...`);
  }
  throw lastErr;
}

module.exports = { callGemini };
