# Troubleshooting Guide

## Common Issues and Solutions

### 1. ChatGPT Not Running / OpenAI API Errors

**Error Message:**
```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

**Root Cause:**
Running Python without activating the virtual environment. The system Python has a different (incompatible) version of the OpenAI library.

**Solution:**

**Option A - Use the batch file (easiest):**
```bash
run.bat
```

**Option B - Activate venv manually:**
```bash
# On Windows:
.\venv\Scripts\activate
python -m src.main

# On macOS/Linux:
source venv/bin/activate
python -m src.main
```

**Option C - Run with venv Python directly:**
```bash
# On Windows:
.\venv\Scripts\python.exe -m src.main

# On macOS/Linux:
./venv/bin/python -m src.main
```

**Verification:**
When venv is active, your command prompt should show `(venv)` prefix:
```
(venv) C:\Users\...\brand-monitoring-tool>
```

---

### 2. Brand Not Appearing as "Organic Competitor"

**Issue:**
A brand mentioned in the query doesn't appear in "Organic competitor 1-3" columns.

**Example:**
Query: "Is GRIDSERVE or ionity better?"
Expected: Ionity in "Organic competitor 1"
Actual: Ionity in "Competitors Mentioned" column

**Explanation:**
This is **correct behavior**! The columns mean:

| Column | Definition | Example |
|--------|------------|---------|
| **Query brand** | Target brand being audited | Gridserve |
| **Organic competitor 1-3** | Brands mentioned in RESPONSES but NOT in query | Be.EV, Pod Point, etc. |
| **Competitors Mentioned** | ALL competitors (from query + responses) | Ionity, Be.EV, Pod Point |

**Why "Organic"?**
"Organic" means the brand appeared naturally in the AI's response without being prompted. If you mention a brand in your question, it's expected to appear in the answer, so it's NOT "organic."

**How to Get Organic Competitors:**
Ask questions that DON'T mention specific competitor names:
- ✓ "What are the best EV charging networks in the UK?"
- ✓ "Which charging provider should I choose?"
- ✗ "Is GRIDSERVE or Ionity better?" (mentions Ionity)

---

### 3. No Results for Specific Platform

**Check 1 - Platform Enabled:**
Verify in [config/config.json](config/config.json#L21-L25):
```json
"platforms": {
  "chatgpt": true,    ← Must be true
  "gemini": true,
  "perplexity": true
}
```

**Check 2 - API Key Set:**
Verify in `.env` file:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=...
```

**Check 3 - Console Output:**
Look for initialization messages:
```
✓ ChatGPT initialized    ← Should see this
✓ Gemini initialized
✓ Perplexity initialized
```

If you see:
```
✗ Failed to initialize chatgpt: [error message]
```
Then there's an API key or connectivity issue.

---

### 4. Rate Limit Errors

**Symptoms:**
- Multiple ✗ marks during processing
- "Rate limit exceeded" errors

**Solutions:**

**Option A - Reduce runs per query:**
Edit [config/config.json](config/config.json#L20):
```json
"runs_per_query": 5    // Instead of 35 or 100
```

**Option B - Increase delay:**
Edit [src/query_processor.py:127](src/query_processor.py#L127):
```python
time.sleep(random.uniform(1.0, 2.0))  # Instead of (0.2, 0.5)
```

**Option C - Check API quotas:**
- ChatGPT: https://platform.openai.com/usage
- Gemini: https://aistudio.google.com/app/apikey
- Perplexity: https://www.perplexity.ai/settings/api

---

### 5. Brand Not Detected in Responses

**Check 1 - Brand Name Match:**
Brand names must match EXACTLY (case-insensitive):

Config:
```json
"competitors": ["Ionity", "Be.EV", "bp pulse"]
```

If responses mention "BP Pulse" (with space), it won't match "bp pulse" - add an alias!

**Solution - Add Aliases:**
```json
"brand_aliases": {
  "bp pulse": ["bp pulse", "BP Pulse", "bppulse"],
  "Be.EV": ["beev", "be ev", "Be.EV"]
}
```

**Check 2 - Test Brand Detection:**
```bash
.\venv\Scripts\python.exe test_brand_detection.py
```

---

### 6. Excel Report Missing Data

**Check console output for:**
- Number of successful runs vs failures
- Platform-specific errors
- Total queries processed

**Example:**
```
ChatGPT: ✓✓✓✓✓ (5/5) [8.2s]    ← All successful
Gemini:  ✓✓✓✗✓ (4/5) [6.1s]    ← One failed
Perplexity: ✗✗✗✗✗ (0/5) [2.3s] ← All failed!
```

If a platform has 0 successful runs, check:
1. API key validity
2. API credit balance
3. Network connectivity
4. API service status

---

### 7. Configuration Not Loading

**Error:**
```
Configuration file not found: config/config.json
```

**Causes:**
1. Running from wrong directory
2. config.json was deleted (it's gitignored)
3. File encoding issues

**Solution:**
1. Ensure you're in project root directory
2. Check file exists: `dir config`
3. If missing, create from template or use web interface

---

## Understanding the Report Columns

### Column Meanings

| Column | What It Shows | How It's Calculated |
|--------|---------------|---------------------|
| **Query** | The question asked | Direct from input |
| **Query brand** | Target brand performance | % of responses mentioning it |
| **Organic competitor 1-3** | Top 3 brands NOT in query | Ranked by mention frequency |
| **Likelihood %** | How often brand appears | (Mentions / Total Runs) × 100 |
| **Position** | Where target appears | First, Second, Third in lists |
| **Competitors Mentioned** | All competitors found | Both from query + responses |
| **Source(s) Cited** | Websites referenced | Domain name + count |
| **Key messages** | Keyword category matches | % of responses with keywords |
| **Tone** | Overall sentiment | P (Positive), N (Negative), N (Neutral) |
| **Style mentioned** | Product models found | Specific model names |

---

## Best Practices

### 1. Query Design

**For Organic Competitor Discovery:**
- ✓ "Best EV charging networks UK 2025"
- ✓ "Which charging provider has best coverage?"
- ✗ "GRIDSERVE vs Ionity" (mentions competitors)

**For Direct Comparison:**
- ✓ "Is GRIDSERVE better than Ionity?"
- ✓ "GRIDSERVE or bp pulse for reliability?"

### 2. Run Configuration

**Testing:** 5 runs per query
**Development:** 10-20 runs per query
**Production:** 35-100 runs per query

### 3. Cost Management

**Approximate costs per 35-run campaign:**
- ChatGPT (gpt-4o): ~$0.50-1.00 per query
- Gemini: ~$0.10-0.20 per query
- Perplexity: ~$0.20-0.40 per query

**Total:** ~$0.80-1.60 per query × number of queries

---

## Getting Help

### Log Files
Currently no log files are generated. Check console output for errors.

### Debug Mode
Run test scripts:
```bash
.\venv\Scripts\python.exe test_brand_detection.py
```

### Report Issues
If you find a bug or need help:
1. Check this troubleshooting guide first
2. Review [00-main-context.md](Contexts/00-main-context.md) for architecture details
3. Check recent context files in `Contexts/` folder
4. Document the issue with console output and screenshots

---

*Last Updated: 2025-12-09*
