# 🎯 Job Application Tracker

**AI-Powered Job Application Tracking with Local Ollama Models**

A privacy-first job application tracker that automatically monitors your Gmail for job-related emails, uses local AI (Ollama) to classify them, and helps you track your job search progress—all running 100% on your local machine.

---

## ✨ Features

- **🔒 Privacy-First**: Everything runs locally—your emails never leave your machine
- **🤖 AI-Powered**: Uses Ollama (local LLMs) for intelligent email classification
- **📧 Gmail Integration**: Automatically fetches and monitors job-related emails
- **📊 Beautiful Dashboard**: Clean, modern UI to track your applications
- **🔄 Auto-Sync**: Background job that checks for new emails periodically
- **🎯 Smart Classification**: Identifies applications, interviews, rejections, and offers
- **👻 Ghost Detection**: Alerts you about applications with no response in 14+ days
- **💯 Zero Cost**: No API fees, no cloud AI—completely free to run

---

## 🏗️ Tech Stack

- **Backend**: Python + FastAPI
- **Database**: SQLite
- **AI**: Ollama (local LLMs)
- **Gmail**: Google Gmail API
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Scheduling**: APScheduler

---

## 📋 Prerequisites

### 1. Python 3.8+
```powershell
python --version
```

### 2. Ollama
Download and install from: https://ollama.ai

After installing, pull a model:
```powershell
ollama pull llama3
```

Start Ollama:
```powershell
ollama serve
```

### 3. Gmail API Credentials
You'll need to set up Gmail API access (free). See [Gmail Setup](#-gmail-api-setup) below.

---

## 🚀 Quick Start

### Step 1: Clone & Install

```powershell
cd "c:\Users\Fateh Ali Aamir\Documents\personal_projects\Job-Application-Tracker"

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```powershell
# Copy example env file
Copy-Item .env.example .env

# Edit if needed (defaults work fine)
```

### Step 3: Set Up Gmail API

Run the setup helper:
```powershell
python scripts\setup_gmail.py
```

Follow the instructions to:
1. Create a Google Cloud project
2. Enable Gmail API
3. Download `credentials.json`
4. Place it in the project root

### Step 4: Initial Sync

Sync your first batch of emails:
```powershell
python scripts\initial_sync.py
```

This will:
- Connect to Gmail (opens browser for OAuth)
- Fetch job-related emails
- Classify them with AI
- Store in database

### Step 5: Run the App

```powershell
python run.py
```

Then open: **http://localhost:8000**

---

## 📧 Gmail API Setup

### Detailed Instructions

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create a New Project**
   - Click "Select a project" → "New Project"
   - Name it (e.g., "Job Tracker")
   - Click "Create"

3. **Enable Gmail API**
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click on it and click "Enable"

4. **Create OAuth Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - If prompted, configure the OAuth consent screen:
     - User Type: External
     - App name: Job Application Tracker
     - User support email: your email
     - Developer contact: your email
     - Save and continue through the screens
   - Back to "Create OAuth client ID":
     - Application type: **Desktop app**
     - Name: Job Tracker Desktop
     - Click "Create"

5. **Download Credentials**
   - You'll see your new OAuth 2.0 Client ID
   - Click the download icon (⬇️) on the right
   - Save the file as `credentials.json`
   - Move it to the project root directory

6. **First Run Authorization**
   - The first time you run the app, it will open your browser
   - Log in with your Google account
   - Click "Allow" to grant Gmail read access
   - The app will save a `token.json` file for future use

---

## 🎨 How It Works

### Architecture

```
┌─────────────┐
│   Gmail     │
│   Inbox     │
└──────┬──────┘
       │
       │ Gmail API
       ▼
┌─────────────┐      ┌──────────────┐
│   Python    │────▶ │   Ollama     │
│   Backend   │      │  (Local AI)  │
└──────┬──────┘      └──────────────┘
       │
       │ SQLite
       ▼
┌─────────────┐
│  Dashboard  │
│   (Browser) │
└─────────────┘
```

### Email Classification

The AI analyzes emails and classifies them as:

- **APPLIED**: Application confirmation received
- **INTERVIEW**: Interview invitation or next steps
- **REJECTION**: Application rejected
- **OFFER**: Job offer received
- **GHOSTED**: No response in 14+ days (auto-detected)
- **OTHER**: General job-related email

### Smart Features

1. **Keyword Detection**: Fast classification for obvious cases
2. **AI Fallback**: Ollama LLM for ambiguous emails
3. **Thread Tracking**: Groups related emails by conversation
4. **Status Progression**: Updates status as conversations evolve
5. **Confidence Scoring**: Shows how confident the AI is

---

## 📁 Project Structure

```
Job-Application-Tracker/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app
│       ├── config.py            # Configuration
│       ├── database.py          # SQLite setup
│       ├── models.py            # Database models
│       ├── gmail_client.py      # Gmail integration
│       ├── ai_classifier.py     # Ollama AI classifier
│       └── scheduler.py         # Background sync
├── frontend/
│   ├── index.html              # Dashboard UI
│   ├── app.js                  # Frontend logic
│   └── styles.css              # Styling
├── scripts/
│   ├── setup_gmail.py          # Gmail setup helper
│   └── initial_sync.py         # Initial email sync
├── run.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore
└── README.md
```

---

## 🔧 Configuration

Edit `.env` to customize:

```bash
# Gmail API
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# Ollama
OLLAMA_MODEL=llama3              # or mistral, codellama, etc.
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_URL=sqlite:///./job_tracker.db

# Sync Settings
SYNC_INTERVAL_MINUTES=30         # How often to check for new emails
MAX_EMAILS_PER_SYNC=50          # Max emails per sync

# Server
HOST=0.0.0.0
PORT=8000
```

---

## 🎯 Usage Guide

### Dashboard Overview

- **Stats Cards**: Quick overview of all applications
- **Sync Button**: Manually trigger email sync
- **Refresh**: Reload data from database
- **Filter**: Filter by status (Applied, Interview, etc.)
- **Applications List**: All tracked applications with details

### Manual Sync

Click "🔄 Sync Emails" to:
1. Fetch latest job emails from Gmail
2. Classify new emails with AI
3. Update existing applications
4. Create new application entries

### Auto-Sync

When running with `python run.py`, the app automatically syncs every 30 minutes (configurable in `.env`).

### Viewing Details

Each application card shows:
- Company name and role
- Current status
- Last email subject and snippet
- Date of last update
- AI confidence score

---

## 🛠️ Advanced Usage

### Use a Different Model

```powershell
# Pull a different Ollama model
ollama pull mistral

# Update .env
# OLLAMA_MODEL=mistral
```

### Increase Sync Frequency

```bash
# In .env
SYNC_INTERVAL_MINUTES=15  # Check every 15 minutes
```

### Process More Emails

```powershell
python scripts\initial_sync.py --max-emails 200
```

### Run Without Auto-Sync

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

---

## 🐛 Troubleshooting

### "Ollama connection failed"

**Solution**: Make sure Ollama is running
```powershell
ollama serve
```

### "Gmail credentials not found"

**Solution**: Download credentials from Google Cloud Console and save as `credentials.json` in project root.

### "ModuleNotFoundError"

**Solution**: Activate virtual environment
```powershell
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### "Too many requests" from Gmail API

**Solution**: Gmail API has rate limits. Reduce `MAX_EMAILS_PER_SYNC` or increase `SYNC_INTERVAL_MINUTES` in `.env`.

### Emails not being classified correctly

**Solutions**:
1. Try a different model: `ollama pull mistral` and update `.env`
2. The classifier uses keywords first, then AI fallback
3. Check email content—some emails are genuinely ambiguous

### Port 8000 already in use

**Solution**: Change port in `.env`:
```bash
PORT=8080
```

---

## 🚀 Future Enhancements

Potential features to add:

- [ ] Email labeling (auto-label in Gmail)
- [ ] Weekly summary emails
- [ ] Chrome extension
- [ ] Export to CSV
- [ ] Application timeline view
- [ ] Salary tracking
- [ ] Company notes
- [ ] Deadline reminders
- [ ] Integration with job boards (LinkedIn, Indeed)
- [ ] Multi-account support

---

## 💡 Tips for Best Results

1. **Run initial sync** with `--max-emails 200` to get all recent job emails
2. **Check the dashboard** daily during active job search
3. **Use filters** to focus on interviews or pending applications
4. **Monitor ghosted** applications—follow up after 2 weeks
5. **Try different models** if classification accuracy is low
6. **Keep Ollama running** for best auto-sync performance

---

## 📊 Privacy & Security

- ✅ All emails processed locally (never sent to cloud)
- ✅ Ollama runs on your machine (no external AI APIs)
- ✅ SQLite database stored locally
- ✅ OAuth tokens encrypted by Google libraries
- ✅ No telemetry or tracking
- ✅ Gmail API uses read-only scope
- ⚠️ Keep `credentials.json` and `token.json` private (they're in `.gitignore`)

---

## 🤝 Contributing

This is a personal project, but feel free to:
- Fork and modify for your needs
- Submit issues if you find bugs
- Share improvements

---

## 📄 License

MIT License - Free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- **Ollama** - Amazing local LLM platform
- **FastAPI** - Modern Python web framework
- **Google Gmail API** - Email access
- **SQLAlchemy** - Database ORM

---

## 📞 Support

If you encounter issues:

1. Check [Troubleshooting](#-troubleshooting)
2. Verify all prerequisites are installed
3. Check Ollama is running: `ollama list`
4. Check Gmail credentials are valid

---

## 🎉 You're All Set!

Start tracking your job applications like a pro. Good luck with your job search! 🚀

```powershell
python run.py
```

Then open: **http://localhost:8000**
