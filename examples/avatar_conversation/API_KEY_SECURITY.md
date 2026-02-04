# 🔐 API Key Security Setup - Complete Guide

## What We Did

✅ **Separated your Groq API key from source code**

Now you can safely push your avatar project to GitHub without exposing secrets.

---

## Files Created

### 1. `.env.example` (Safe Template ✅)
Shows what environment variables are needed. Safe to commit.

```env
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
```

**What others do:**
```bash
cp .env.example .env
# Edit .env with their own API key
```

### 2. `.env` (Your Secrets 🔒)
Contains your actual API key. Protected by `.gitignore`.

```env
GROQ_API_KEY=gsk_abc123...  ← Your real key (private!)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
```

**Only on your machine, never committed to git.**

### 3. `.gitignore` (Already Had It ✅)
Already includes `.env*` pattern that protects all `.env` files.

### 4. Documentation Files (Safe ✅)
- `ENV_SETUP.md` - How to set up
- `PRE_PUSH_CHECKLIST.md` - Security verification
- `READY_TO_PUSH.md` - Push instructions
- `FILES_TO_COMMIT.md` - What files to include

---

## How It Works

### For You (Developer)
```
1. You have: .env (with your API key)
   └─ Only on your computer
   └─ Never pushed to git
   └─ Added to .gitignore

2. Code loads from .env:
   from dotenv import load_dotenv
   load_dotenv()
   api_key = os.getenv('GROQ_API_KEY')

3. You push: Everything EXCEPT .env
   └─ All source code (safe)
   └─ .env.example (template)
   └─ Documentation
   └─ Tests
```

### For Others (Cloners)
```
1. They clone your repo
   └─ Get all code
   └─ Get .env.example
   └─ Don't get .env (it's in .gitignore)

2. They set up their own:
   cp .env.example .env
   # Edit .env with their own API key

3. They run the app:
   python backend.py
```

---

## Step-by-Step: What to Do Now

### Step 1: Update Your `.env` File ✏️

Open `.env` and add your real Groq API key:

```bash
# Open the file
code examples/avatar_conversation/.env

# Edit to add your actual key:
GROQ_API_KEY=gsk_YOUR_REAL_KEY_HERE
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
```

### Step 2: Verify Protection ✅

```bash
# Check that .env is protected
cd examples/avatar_conversation
git check-ignore .env

# Should output: .env
# (This means git will ignore it)
```

### Step 3: Verify It Works 🧪

```bash
# Test that everything loads correctly
python test_integration.py

# Should show:
# ✓ GROQ_API_KEY found
# ✓ All tests passing
```

### Step 4: Review Files Before Commit 👀

```bash
# See what will be committed
git status

# Should show:
# ✅ src/pipecat/processors/avatar/sadtalker_processor.py
# ✅ src/pipecat/processors/avatar/liveportrait_processor.py
# ✅ examples/avatar_conversation/.env.example
# ✅ examples/avatar_conversation/ENV_SETUP.md
# ... and more

# Should NOT show:
# ❌ examples/avatar_conversation/.env
```

### Step 5: Commit ✔️

```bash
git add .
git commit -m "Add real SadTalker + ONNX optimization with secure API key storage

Features:
- Audio-to-motion synthesis using mel-spectrogram
- 63-channel FLAME facial coefficients
- ONNX photorealistic rendering
- Optimized tensor dimensions
- 14.18ms latency (60+ FPS)

Security:
- Secure API key storage in .env (protected)
- .env.example template for contributors
- Complete setup documentation

Tests:
- All 6/6 integration tests passing
- Real-time performance validated"

git push origin main
```

---

## Security Details

### What's Protected 🔒

```
.env
├─ GROQ_API_KEY=gsk_...     (Your secret!)
├─ OLLAMA_BASE_URL=...      (Optional, less sensitive)
└─ OLLAMA_MODEL=...         (Optional, not sensitive)
```

All protected by:
1. **`.gitignore`** - Git never tracks `.env*` files
2. **`git check-ignore`** - Verification that it's protected
3. **`git status`** - Won't show `.env` before push

### What's Exposed ✅

```
.env.example (THIS IS SAFE!)
├─ Shows what variables are needed
├─ Template with example values
├─ Committed to git (everyone sees it)
└─ BUT contains NO REAL secrets
```

---

## If Your Key Gets Exposed 🚨

**Don't panic! Here's what to do:**

### Immediate Action (1 minute)
```bash
# 1. Rotate the key immediately
# https://console.groq.com/keys
# → Delete the old key
# → Generate a new key

# 2. Update your .env
GROQ_API_KEY=gsk_NEW_KEY_HERE

# 3. Verify git status (should show clean)
git status
```

### If Already Pushed (5 minutes)
```bash
# Remove .env from git history
git filter-branch --tree-filter 'rm -f .env' HEAD

# Force push (careful!)
git push --force-all
```

---

## Verification Commands

### Before Every Push
```bash
# 1. Check .env is ignored
git check-ignore .env
# Output: .env

# 2. Check no secrets in commits
git diff --cached | grep -i "gsk_"
# Output: (nothing - good!)

# 3. Check status
git status
# Should NOT show: .env
```

### After Push
```bash
# Verify on GitHub
# Visit: https://github.com/YOUR_USERNAME/YOUR_REPO

# You should see:
# ✅ .env.example (safe)
# ❌ NO .env (protected)
```

---

## Best Practices

### ✅ Do This
- Keep `.env` in `.gitignore`
- Update `.env.example` when adding new config
- Rotate keys periodically
- Document required variables
- Use `load_dotenv()` in code

### ❌ Don't Do This
- Commit `.env` files with real keys
- Hardcode API keys in source files
- Share `.env` with others
- Leave old keys active
- Post API keys in logs

---

## Code Integration

Your code already loads from `.env`:

```python
# In backend.py
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Access your API key
groq_api_key = os.getenv('GROQ_API_KEY')
```

This is secure because:
1. `python-dotenv` reads from `.env` (local file)
2. `.env` is never in git (in `.gitignore`)
3. API key only in memory during execution
4. Never exposed in logs or commits

---

## Final Checklist

Before pushing:
- [ ] `.env` exists with your real API key
- [ ] `git check-ignore .env` shows `.env` is protected
- [ ] `git status` does NOT show `.env`
- [ ] `.env.example` IS included in commit
- [ ] `test_integration.py` passes (tests load from `.env`)
- [ ] No API keys in any `.py` files
- [ ] Documentation updated

Then:
```bash
git push origin main
```

---

## You're Secure! 🎉

✅ Your Groq API key is protected
✅ Others can clone and set up easily
✅ Safe to push to public GitHub
✅ Professional security practices

**Everything is ready!**

---

## Questions?

| Question | Answer |
|----------|--------|
| Where is my API key stored? | In `.env` (your computer only) |
| Will git track `.env`? | No, it's in `.gitignore` |
| Do I need to edit `.env`? | Yes, add your real API key |
| What is `.env.example`? | Safe template (can be committed) |
| Can others see my key? | No, `.env` is not in git |
| What if I lose `.env`? | Just copy `.env.example` again |
| Is this production-ready? | Yes! Same pattern used by all companies |

---

**You're ready to push!** 🚀

