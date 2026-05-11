# 🚀 Quick Start Guide

This is the fastest way to get your Job Application Tracker running!

## ⚡ 5-Minute Setup

### 1. Install Ollama
```powershell
# Download from: https://ollama.ai
# After installing:
ollama pull llama3
ollama serve
```
Leave this terminal open!

### 2. Set Up Gmail API (5 minutes)

1. Go to: https://console.cloud.google.com/
2. Create project → Enable Gmail API
3. Create OAuth credentials (Desktop app)
4. Download as `credentials.json` → Put in project folder

**Run this for detailed help:**
```powershell
python scripts\setup_gmail.py
```

### 3. Install & Run

**Option A: Use batch files (Windows)**
```powershell
# First time setup
.\setup.bat

# Then run
.\start_app.bat
```

**Option B: Manual**
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install
pip install -r requirements.txt

# Setup environment
Copy-Item .env.example .env

# Initial sync
python scripts\initial_sync.py

# Run app
python run.py
```

### 4. Open Dashboard

Go to: **http://localhost:8000**

Click "🔄 Sync Emails" to start!

---

## 🎯 What Happens Next?

1. **First sync**: App opens browser for Gmail auth
2. **AI classification**: Ollama analyzes your emails
3. **Dashboard shows**: All your job applications organized
4. **Auto-sync**: Checks for new emails every 30 min

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Ollama connection failed" | Run `ollama serve` in another terminal |
| "Gmail credentials not found" | Download `credentials.json` from Google Cloud |
| "ModuleNotFoundError" | Activate venv: `.\venv\Scripts\Activate` then `pip install -r requirements.txt` |
| Port 8000 in use | Change `PORT=8080` in `.env` |

---

## 📚 Full Documentation

See [README.md](README.md) for complete details!

---

## 🎉 That's It!

You now have a fully functional, privacy-first job application tracker running locally!

**Pro Tips:**
- Keep Ollama running for best performance
- Run initial sync with more emails: `python scripts\initial_sync.py --max-emails 200`
- Try different models: `ollama pull mistral` (update `.env`)
