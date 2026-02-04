# ✅ Pre-Push Security Checklist

## Before You Push to Git

**Important**: Never commit API keys, secrets, or sensitive data!

---

## Quick Check (< 1 minute)

```bash
# 1. Verify .env is NOT in git
git status

# Expected: .env should NOT appear in the list

# 2. Double-check no secrets in code
grep -r "gsk_" src/
grep -r "GROQ_API_KEY=" *.py

# Expected: No results (secrets only in .env, not in code)

# 3. Verify .gitignore includes .env
cat .gitignore | grep "\.env"

# Expected: Output shows ".env*"

# 4. Safe to push!
git push origin main
```

---

## Files Included (Safe to Push ✅)

```
✅ .env.example          - Safe template for configuration
✅ backend.py           - Source code
✅ test_integration.py  - Tests
✅ sadtalker_processor.py - Avatar code
✅ liveportrait_processor.py - Avatar code
✅ All markdown docs    - Documentation
✅ config.yaml          - Public config
```

## Files Excluded (Protected 🔒)

```
🔒 .env                 - Your actual API keys (ignored by git)
🔒 __pycache__/         - Python cache
🔒 .venv/              - Virtual environment
🔒 *.log               - Log files
```

---

## Groq API Key Security

### ✅ You're Protected If:
- [ ] `.env` is in `.gitignore`
- [ ] `.env` doesn't appear in `git status`
- [ ] API key is only in `.env`, not in source code
- [ ] You haven't committed `.env` yet

### ⚠️ If Accidentally Exposed:
1. **Immediately rotate the key**:
   - https://console.groq.com/keys
   - Delete old key
   - Generate new key
   - Update `.env` with new key

2. **Remove from git history** (if already pushed):
   ```bash
   # Remove from all commits
   git filter-branch --tree-filter 'rm -f .env' HEAD
   
   # Force push (careful!)
   git push --force-all
   ```

3. **Don't panic** - Groq will disable the old key if needed

---

## Git Commands Cheat Sheet

```bash
# Check what will be pushed
git diff --cached --name-only

# Verify .env is ignored
git check-ignore -v .env

# See all ignored files
git status --ignored

# Remove .env if accidentally added
git rm --cached .env
git commit -m "Remove .env from tracking"
```

---

## One-Time Setup

```bash
# 1. Set up .env
cp .env.example .env
# Edit .env and add your Groq API key

# 2. Verify git ignore
git check-ignore .env
# Should output: .env

# 3. Test it works
python test_integration.py

# 4. Now safe to push!
git add .
git commit -m "Add avatar pipeline with SadTalker and ONNX optimization"
git push origin main
```

---

## Verify Before Every Push

```bash
# BEFORE pushing, run:
git status

# Should show ONLY files you want to commit
# Should NOT show:
#   ❌ .env
#   ❌ __pycache__/
#   ❌ .venv/
#   ❌ *.pyc
#   ❌ .log files
```

---

## Files You're Pushing

### Code (✅ Safe)
- `src/pipecat/processors/avatar/sadtalker_processor.py` - Real audio-to-motion
- `src/pipecat/processors/avatar/liveportrait_processor.py` - ONNX inference
- `src/pipecat/processors/avatar/motion_vector_frame.py` - Data structure
- `examples/avatar_conversation/backend.py` - Main app

### Documentation (✅ Safe)
- `PHASE_3_COMPLETE.md` - Technical details
- `QUICK_START.md` - Quick reference
- `ENV_SETUP.md` - Environment guide
- `INTEGRATION_TEST_REPORT.md` - Test results
- All other `.md` files

### Configuration (✅ Safe)
- `.env.example` - Template (no secrets)
- `config.yaml` - Public settings
- `requirements.txt` - Dependencies

### Tests (✅ Safe)
- `test_integration.py` - All tests
- `test_pipeline.py` - Pipeline tests

---

## What NOT to Push

```
❌ .env                    - Contains your API key
❌ __pycache__/           - Python cache (in .gitignore)
❌ .venv/ or venv/       - Virtual environment (in .gitignore)
❌ *.log                  - Log files (in .gitignore)
❌ .DS_Store              - macOS files (in .gitignore)
❌ node_modules/          - Node packages (in .gitignore)
```

All of these are already in `.gitignore`, so they won't be included.

---

## Final Verification

```bash
# Run this final check before pushing
echo "=== Checking .env protection ==="
git check-ignore -v .env
echo ""
echo "=== Files to be committed ==="
git diff --cached --name-only | head -20
echo ""
echo "If .env appears above, DO NOT PUSH!"
echo "If .env does NOT appear, you're safe!"
```

---

## You're Ready! 🎉

When you see:
```
✅ .env is ignored by git
✅ No secrets in source files
✅ All tests passing
✅ Documentation complete
```

Then you can safely push:
```bash
git push origin main
```

---

**Questions?** Check `ENV_SETUP.md` for detailed environment configuration.

