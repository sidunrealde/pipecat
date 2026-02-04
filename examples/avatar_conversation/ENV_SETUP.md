# 🔐 Environment Setup Guide

## Overview

The avatar conversation backend requires API keys and configuration. These **must be kept secret** and never committed to version control.

---

## Setup Steps

### 1. Copy the Example File
```bash
cp .env.example .env
```

### 2. Get Your Groq API Key
1. Visit https://console.groq.com/keys
2. Create a new API key (free tier available)
3. Copy the key

### 3. Update `.env` File
Edit `.env` and replace:
```
GROQ_API_KEY=your_groq_api_key_here
```

with your actual key:
```
GROQ_API_KEY=gsk_abc123xyz...
```

### 4. Verify Setup
Run the test:
```bash
python test_integration.py
```

You should see:
```
✓ GROQ_API_KEY found
✓ All tests passing
```

---

## File Structure

```
avatar_conversation/
├── .env                 ← YOUR SECRETS (do NOT commit)
├── .env.example         ← Template (safe to commit)
├── backend.py
├── config.yaml
└── ... other files
```

---

## Security Checklist

- ✅ `.env` is in `.gitignore` (checked by git before commit)
- ✅ `.env.example` is a safe template (CAN be committed)
- ✅ Never paste your real API key in code
- ✅ Never commit `.env` files with real keys
- ✅ Rotate keys if accidentally exposed

### Git Safety Check
```bash
# Before pushing, verify .env is ignored
git status

# Should NOT show .env in the list
# Should only show files you want to commit
```

---

## Environment Variables

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `GROQ_API_KEY` | Yes | https://console.groq.com/keys | Speech-to-text & text-to-speech |
| `OLLAMA_BASE_URL` | No | Local Ollama | LLM inference server |
| `OLLAMA_MODEL` | No | Local Ollama | Which model to use |

---

## Loading in Code

The code uses `python-dotenv` to load from `.env`:

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
groq_key = os.getenv('GROQ_API_KEY')
ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
```

---

## Troubleshooting

### "GROQ_API_KEY not found"
1. Check `.env` file exists in same directory as `backend.py`
2. Verify you added your key correctly
3. Restart terminal/IDE

### "Invalid API key"
1. Double-check key is copied exactly (no spaces)
2. Verify key is still active on https://console.groq.com/keys
3. Try generating a new key

### ".env file showing in git"
1. This means `.env` was tracked before `.gitignore` was added
2. Remove it:
   ```bash
   git rm --cached .env
   git commit -m "Remove .env from tracking"
   ```

---

## Best Practices

✅ **DO:**
- Keep `.env` in `.gitignore`
- Use `.env.example` as template
- Rotate keys periodically
- Use environment variables in code
- Document required variables

❌ **DON'T:**
- Commit `.env` with real keys
- Hardcode API keys in source files
- Share `.env` files with others
- Use same key in dev/prod
- Post API keys in logs

---

## For Pushes to Git

Before pushing, verify:
```bash
# Check that .env is NOT in the commit
git diff --cached --name-only

# Should NOT list .env
# Should be safe to push

# Then push
git push origin main
```

---

## Reference

- **Groq API Docs**: https://console.groq.com/docs
- **Python-dotenv**: https://github.com/thesketh/python-dotenv
- **Git Ignore**: https://git-scm.com/docs/gitignore

---

**You're secure!** The `.env` file with your API key is protected. ✅
