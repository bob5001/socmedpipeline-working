# Quick Start Guide

Get your pipeline running in 5 minutes.

## Prerequisites Check

```bash
# 1. Check Python version (needs 3.10+)
python3 --version

# 2. Check if Ollama is installed
ollama --version

# 3. Check if Ollama is running
ollama list
```

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Pull Ollama Models

```bash
# Text generation model (~2GB)
ollama pull llama3.1

# Vision model (~4GB)
ollama pull llava:7b
```

### 3. Start Ollama (if not running)

```bash
ollama serve
# Keep this terminal open, or run in background
```

### 4. Configure Replicate API

Your `.env` already has the API key. Verify it's correct:

```bash
cat .env
# Should show: REPLICATE_API=r8_...
```

## Test Run

### Option A: Full Pipeline

Run all six agents sequentially:

```bash
python run_pipeline.py
```

You'll be prompted between each task to continue or stop.

### Option B: Individual Agents

Test one agent at a time:

```bash
# Task 1: Generate posts from campaign brief
python src/agent_1_campaign_data.py
```

This will:
- Read `Signal Sanctuary — EHS Awareness Campa.md`
- Call Ollama llama3.1 to generate 5 posts
- Create `posts-queue.csv`

Expected output:
```
Agent 1: Campaign Data Generation
==================================================
Reading campaign brief from Signal Sanctuary — EHS Awareness Campa.md
Generating posts using llama3.1...
✓ Created 5 posts in posts-queue.csv

Generated Posts:
  - SS-20240209-143022: pattern_recognition
  - SS-20240209-143023: normalization
  - SS-20240209-143024: gentle_orientation
  ...

✓ Task 1 complete. Ready for git commit.
```

### Next Steps After Task 1

```bash
# Commit the generated posts
git add posts-queue.csv
git commit -m "Generated campaign posts from brief"

# Run Task 2: Generate images (costs ~$0.05 for 5 images)
python src/agent_2_image_generation.py
```

## Expected Costs

- **Ollama (local)**: Free
- **Replicate (images)**: ~$0.01 per image
- **Full pipeline for 5 posts**: ~$0.05

## Troubleshooting

### "ollama: command not found"

Install Ollama:
```bash
# macOS
brew install ollama

# Or download from https://ollama.ai
```

### "Connection refused" from Ollama

Start the Ollama server:
```bash
ollama serve
```

### "Invalid Replicate API token"

Check your `.env` file has the correct key:
```bash
# Should start with r8_
REPLICATE_API=r8_your_token_here
```

### Vision audit rejects all images

The vision model is strict about tone. Check:
1. Image prompts emphasize calm, minimalist aesthetics
2. No faces, no text in generated images
3. Architectural/environmental focus

### Python import errors

Make sure you're in the project directory:
```bash
cd /Users/robertkoch/Projects/socmedpipeline-claude
python run_pipeline.py
```

## What You'll Get

After running the full pipeline:

```
images/
  ├── SS-20240209-143022.png         # Generated image
  ├── SS-20240209-143022-final.png   # With text overlay
  ├── SS-20240209-143023.png
  ├── SS-20240209-143023-final.png
  └── ...

posts-queue.csv                      # Complete with all statuses
pipeline-status.json                 # Status report
```

5 draft posts ready for Facebook Business Manager review!

## Notes

- **Agent 4** (Affinity Designer) is a placeholder - it copies images for now
- **Agent 6** (Facebook) is a placeholder - it logs what would be posted
- Both can be implemented when MCP/API access is available

## Next Steps

1. Review generated posts in `posts-queue.csv`
2. Check images in `images/` directory
3. Read `pipeline-status.json` for completion status
4. Implement Agent 4 & 6 integrations if needed
5. Run for different campaigns by updating campaign brief

Happy posting! 🚀
