# Streamlit Cloud Deployment Checklist

## ✅ Preparation Complete

The framework is now ready for Streamlit Cloud deployment! Here's your step-by-step deployment guide:

## Step 1: GitHub Repository Setup

**Option A: Create New Repository**
1. Go to [GitHub.com](https://github.com)
2. Click "New repository"
3. Name it: `ai-coaching-framework`
4. Make it public (required for free Streamlit Cloud)
5. Don't initialize with README (we have files already)

**Option B: Use Existing Repository**
If you already have a repo, make sure it's public for free Streamlit Cloud hosting.

## Step 2: Upload Code to GitHub

```bash
# Navigate to your project
cd "/Users/rs07/Desktop/Projects/Coach Project/ai-coaching-framework"

# Initialize git (if not already done)
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit: AI Performance Coaching Framework v2.0"

# Connect to your GitHub repository (replace with your URL)
git remote add origin https://github.com/YOUR_USERNAME/ai-coaching-framework.git

# Push to GitHub
git push -u origin main
```

## Step 3: Deploy on Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app"
   - Select your repository: `YOUR_USERNAME/ai-coaching-framework`
   - Set main file path: `app.py`
   - Choose branch: `main`

3. **Configure Secrets**
   Click on "Advanced settings" → "Secrets" and add:

   ```toml
   OPENAI_API_KEY = "your_actual_openai_api_key_here"
   DEFAULT_MODEL = "gpt-5"
   REASONING_EFFORT = "medium"
   VERBOSITY = "medium"
   MAX_TOKENS = 4000
   TEMPERATURE = 0.1
   DEFAULT_INTERVAL_MINUTES = 2
   MAX_CONTEXT_WINDOWS = 3
   RETRY_ATTEMPTS = 3
   TIMEOUT_MS = 60000
   ENABLE_LOGGING = true
   AUTO_SUMMARY = true
   ```

4. **Deploy**
   - Click "Deploy!"
   - Wait for deployment (usually 2-5 minutes)

## Step 4: Test Deployment

Once deployed, test these features:

1. **System Test**
   - Go to the "System Test" tab
   - Click "Run Configuration Test"
   - Verify all tests pass ✅

2. **Sample Analysis**
   - Go to "Analysis" tab
   - Paste the sample JSON from `examples/sample_frames.json`
   - Select a template (e.g., "efficiency_focused")
   - Click "Start Analysis"

3. **Export Results**
   - Check that JSON/CSV export works in the "Results" tab

## Step 5: Custom Domain (Optional)

For a custom domain:
1. In Streamlit Cloud, go to your app settings
2. Add your custom domain
3. Configure DNS settings as instructed

## What You Need to Provide:

1. **OpenAI API Key**: Your actual API key for GPT-5 access
2. **GitHub Username**: So I can provide the exact git commands
3. **Repository Name**: If you want something different than `ai-coaching-framework`

## Files Ready for Deployment:

✅ `.streamlit/config.toml` - Streamlit configuration
✅ `.streamlit/secrets.toml.example` - Template for secrets
✅ `.gitignore` - Excludes sensitive files
✅ `requirements.txt` - Python dependencies
✅ `app.py` - Main Streamlit application
✅ Updated `src/config.py` - Handles Streamlit secrets
✅ Sample data and documentation

## Post-Deployment Features:

Once live, your users can:
- 📊 **Analyze frame descriptions** via web interface
- 🎯 **Choose coaching templates** (efficiency, automation, learning, etc.)
- ⚙️ **Configure AI settings** (model, reasoning effort, temperature)
- 📈 **View real-time progress** during analysis
- 📄 **Export results** as JSON or CSV
- 🔧 **Test system health** with built-in diagnostics

## Troubleshooting:

**If deployment fails:**
1. Check the Streamlit Cloud logs
2. Verify all secrets are properly set
3. Ensure repository is public
4. Check that `requirements.txt` has all dependencies

**If API calls fail:**
1. Verify OpenAI API key is correct in secrets
2. Check you have GPT-5 access enabled
3. Monitor API usage limits

**Performance optimization:**
- The app handles large JSON files efficiently
- Progress tracking prevents timeout issues
- Error handling provides clear user feedback

## Ready to Deploy! 🚀

Just provide me with:
1. Your GitHub username
2. Your OpenAI API key (for the secrets configuration)
3. Any custom repository name preference

And I'll give you the exact commands to run!