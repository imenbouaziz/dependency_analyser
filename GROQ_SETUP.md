# Groq API Setup Guide

## Why Groq?

✅ **100% FREE** - No credit card required  
✅ **Super FAST** - Up to 500 tokens/second  
✅ **No Network Issues** - Works behind corporate proxies  
✅ **Latest Models** - Llama 3.1 70B, Mixtral, and more  

---

## Quick Setup (5 minutes)

### Step 1: Get Your Free API Key

1. Go to **https://console.groq.com/**
2. Sign up with your email (free, no credit card)
3. Go to **https://console.groq.com/keys**
4. Click "Create API Key"
5. Copy your key (starts with `gsk_...`)

### Step 2: Add Your API Key

Open `agent/llm.py` and replace the empty string:

```python
GROQ_API_KEY = "gsk_your_actual_key_here"
```

**OR** set it as an environment variable:

```powershell
$env:GROQ_API_KEY="gsk_your_actual_key_here"
```

### Step 3: Test It!

```powershell
python
```

Then in Python:
```python
from agent.llm import create_ollama_client

# Create client
client = create_ollama_client()

# Test it
response = client.invoke([{"role": "user", "content": "Hello!"}])
print(response["content"])
```

---

## Available Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-70b-versatile` | Medium | Excellent | Complex analysis (DEFAULT) |
| `llama-3.1-8b-instant` | Very Fast | Good | Quick queries |
| `mixtral-8x7b-32768` | Fast | Excellent | Long context (32K tokens) |
| `gemma2-9b-it` | Fast | Good | Lightweight tasks |

To change the model, edit `agent/llm.py`:
```python
client = create_ollama_client(model_id="llama-3.1-8b-instant")
```

---

## Rate Limits (Free Tier)

- **30 requests/minute**
- **6,000 tokens/minute**
- **14,400 requests/day**

This is more than enough for dependency analysis!

---

## Troubleshooting

### "Please set your Groq API key"
→ You need to add your API key in `agent/llm.py` or set `GROQ_API_KEY` environment variable

### "Rate limit exceeded"
→ Wait 60 seconds. Free tier is very generous but has limits.

### "Invalid API key"
→ Double-check you copied the full key from https://console.groq.com/keys

---

## Why Groq?

Groq offers:
- No downloads needed ✅
- Works everywhere (API-based) ✅
- Lightning fast inference ✅
- Zero local resources ✅
- Free tier with generous limits ✅

---

## Next Steps

Once your API key is set:

```bash
# Run the UI
.\run_ui.bat

# Or use the agent
python agent/agent_runner.py
```

Enjoy blazing-fast dependency analysis! 🚀
