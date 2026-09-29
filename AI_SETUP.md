# Pathari Bot — Real AI setup

## Option A — Admin panel
1. Login `/admin` → **Settings**
2. Scroll to **Pathari AI (I$H)**
3. Enable AI
4. Paste API key
5. Base URL examples:
   - xAI Grok: `https://api.x.ai/v1`
   - OpenAI: `https://api.openai.com/v1`
6. Model examples:
   - `grok-2-latest` / `grok-3` (xAI)
   - `gpt-4o-mini` (OpenAI)
7. Optional: edit system prompt (personality)
8. Save

## Option B — Vercel env
- `AI_API_KEY`
- `AI_API_BASE` (default https://api.x.ai/v1)
- `AI_MODEL` (default grok-2-latest)

Without a key, Pathari still answers club FAQ (matches, shop, membership) offline.
