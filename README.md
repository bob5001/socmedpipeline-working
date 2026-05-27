# socmedpipeline-working

**The backend pipeline for a complete AI-driven social media generation system.**

This is an active iteration of an earlier project (`socmedpipeline`, Feb 2026). The original pipeline proved the concept using a hand-written markdown brief. This version is the backend half of a two-repo system:

| Repo | Role |
|------|------|
| [`socmedpipeline-frontend`](https://github.com/bob5001/socmedpipeline-frontend) | Next.js app — interviews a business owner via AI chat, scrapes their website, and produces a structured `brief.json` |
| **this repo** | Python pipeline — consumes the brief JSON and runs it through six agents to generate, QA, and schedule social media posts |

### End-to-end flow

```
Business owner
    ↓  (chat interview + website scrape)
socmedpipeline-frontend  →  briefs/{brief_id}.json
    ↓  (python run_pipeline.py --brief ...)
Agent 1: Post content generation   (Ollama llama3.1)
Agent 2: Image generation          (Replicate SDXL)
Agent 3: Vision QA                 (Ollama llava:7b)
Agent 4: Design overlay            (Pillow)
Agent 5: Queue management
Agent 6: Instagram scheduling      (Meta Graph API)
    ↓
campaigns/{brief_id}/posts-queue.csv  +  images/
```

Each brief produces an isolated output directory under `campaigns/{brief_id}/` so multiple clients can run in parallel without stomping each other.

---

## Overview

This pipeline orchestrates six sequential agents to transform a campaign brief into publication-ready social media posts:

```
Campaign Brief → Content Generation → Image Generation → Vision QA →
Design Overlay → Status Tracking → Instagram Drafts
```

## Architecture

### Agents

1. **Agent 1: Campaign Data Generation**
   - Reads campaign brief markdown
   - Uses Ollama (llama3.1) to generate post content
   - Creates `posts-queue.csv` with structured post data

2. **Agent 2: Image Generation**
   - Reads CSV for pending images
   - Generates images via Replicate API (Stable Diffusion SDXL)
   - Saves images to `images/{post_id}.png`

3. **Agent 3: Vision Audit**
   - Uses Ollama (llava:7b) vision model
   - Verifies images match prompts and campaign tone
   - Approves or rejects each image

4. **Agent 4: Design Overlay**
   - Applies text overlays (caption + hashtags)
   - Uses Python Pillow (PIL) for image composition
   - Exports final images to `images/{post_id}-final.png`

5. **Agent 5: Queue Management**
   - Verifies pipeline completion
   - Generates status report JSON
   - Marks posts ready for Facebook

6. **Agent 6: Instagram Integration**
   - Schedules posts via Instagram Graph API
   - Uploads to Instagram Business accounts
   - Schedules 7 days ahead for review (configurable)
   - **Never publishes immediately** (scheduled only)

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) installed and running locally
- Replicate API account and token
- (Optional) Instagram Business account + Graph API credentials
- (Optional) Image hosting service (AWS S3, Cloudinary, etc.)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull llama3.1
ollama pull llava:7b

# Configure environment
cp .env.example .env
# Edit .env and add your REPLICATE_API token
```

### Configuration

All settings are in `config/settings.py`:

- **Ollama models**: `llama3.1` (text), `llava:7b` (vision)
- **Replicate model**: Stable Diffusion SDXL
- **Image size**: 1024x1024px
- **Paths**: CSV queue, images directory, status JSON

## Usage

### Run Complete Pipeline

```bash
# With a brief from the frontend (recommended)
python run_pipeline.py --brief /path/to/briefs/brief-XXXXXXXXXXXX.json

# Legacy: uses CAMPAIGN_BRIEF_PATH from config/settings.py
python run_pipeline.py
```

Pass `--focus general` (default) for any business brief. Use `--focus symptoms` only for the original Signal Sanctuary EHS campaign.

Output is isolated to `campaigns/{brief_id}/` automatically when `--brief` is supplied.

### Run Individual Agents

```bash
# Task 1: Generate posts from campaign brief
python src/agent_1_campaign_data.py

# Task 2: Generate images
python src/agent_2_image_generation.py

# Task 3: Vision audit
python src/agent_3_vision_audit.py

# Task 4: Design overlay
python src/agent_4_design_overlay.py

# Task 5: Status tracking
python src/agent_5_queue_management.py

# Task 6: Facebook drafts
python src/agent_6_facebook_integration.py
```

### Git Workflow

Each agent suggests a commit message. Example workflow:

```bash
# After Task 1
git add posts-queue.csv
git commit -m "Generated campaign posts from brief"

# After Task 2
git add posts-queue.csv images/
git commit -m "Generated images for posts"

# Continue for each task...
```

## Data Flow

### posts-queue.csv

Main state tracking file with columns:

| Column | Description | Values |
|--------|-------------|--------|
| `post_id` | Unique timestamp-based ID | `SS-20240209-143022` |
| `campaign_id` | Campaign identifier | `signal-sanctuary-ehs-awareness` |
| `content_pillar` | Content category | `pattern_recognition`, `normalization`, `gentle_orientation` |
| `image_prompt` | Stable Diffusion prompt | Detailed scene description |
| `caption` | Post text (40-80 words) | Campaign-aligned copy |
| `hashtags` | Space-separated tags | `#wellness #awareness` |
| `image_status` | Image generation state | `pending`, `generated`, `failed` |
| `vision_status` | Vision audit state | `pending`, `approved`, `rejected` |
| `design_status` | Text overlay state | `pending`, `complete` |
| `facebook_status` | Publishing state | `pending`, `ready`, `draft_created` |

### pipeline-status.json

Status report generated by Agent 5:

```json
{
  "timestamp": "2024-02-09T14:30:00",
  "total_posts": 5,
  "statistics": {
    "image_generated": 5,
    "vision_approved": 5,
    "design_complete": 5,
    "ready_for_facebook": 5
  },
  "completion_rate": "5/5",
  "blockers": [],
  "ready_for_posting": true
}
```

## Reference Campaign: Signal Sanctuary

The original test campaign (`Signal Sanctuary — EHS Awareness Campa.md`) remains in the repo as a reference brief. Run it with:

```bash
python run_pipeline.py --focus symptoms
```

## Integration Notes

### Ollama (Local LLM)

- **Text generation**: `llama3.1` for post content
- **Vision audit**: `llava:7b` for image verification
- **Cost**: Free (local inference)
- **Speed**: ~5-10s per request on decent hardware

### Replicate API

- **Image generation**: Stable Diffusion SDXL
- **Cost**: ~$0.01 per image
- **Speed**: ~30-60s per image
- **API key**: Required in `.env`

### Pillow (PIL)

- **Text overlays**: Caption and hashtag composition
- **Design**: Semi-transparent dark overlay with white text
- **Typography**: System fonts (Helvetica/SF/DejaVu/Arial)
- **Cost**: Free (local processing)

### Instagram Graph API

Agent 6 schedules posts to Instagram Business accounts:

**Setup Required:**
1. Instagram Business or Creator account
2. Connected Facebook Page
3. Facebook Developer app with Instagram API
4. Long-lived access token (60 days)
5. Public image hosting (S3, Cloudinary, etc.)

**See detailed setup:** `INSTAGRAM_API_SETUP.md`

**Features:**
- Schedules posts 7 days ahead (configurable)
- Requires public image URLs
- Uses official Meta API
- Free (within rate limits)

## Project Structure

```
socmedpipeline-claude/
├── config/
│   ├── __init__.py
│   └── settings.py              # All configuration
├── src/
│   ├── __init__.py
│   ├── agent_1_campaign_data.py
│   ├── agent_2_image_generation.py
│   ├── agent_3_vision_audit.py
│   ├── agent_4_design_overlay.py
│   ├── agent_5_queue_management.py
│   └── agent_6_facebook_integration.py
├── images/                       # Generated images (gitignored)
├── .env                          # API keys (gitignored)
├── .gitignore
├── posts-queue.csv               # Main state file
├── pipeline-status.json          # Status report (gitignored)
├── requirements.txt
├── run_pipeline.py               # Main orchestrator
├── README.md
└── Signal Sanctuary — EHS Awareness Campa.md  # Campaign brief
```

## Development

### Adding New Campaigns

1. Create new campaign brief markdown in project root
2. Update `CAMPAIGN_BRIEF_PATH` in `config/settings.py`
3. Run Agent 1 to generate new posts

### Modifying CSV Schema

1. Update `CSV_COLUMNS` in `config/settings.py`
2. Update all agent scripts to handle new columns
3. Regenerate `posts-queue.csv`

### Error Recovery

- **Image generation fails**: Check Replicate API key and quota
- **Vision audit rejects images**: Review prompts for tone alignment
- **Ollama connection error**: Ensure Ollama is running (`ollama serve`)

## Success Criteria

✅ All six agents complete in sequence
✅ Final output: Draft posts in Facebook Business Manager
✅ No images published to live social media
✅ All work committed to Git with clear messages

## License

Private project - All rights reserved
