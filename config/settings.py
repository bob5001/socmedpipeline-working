"""Configuration settings for the social media pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent

# Root for anything that must survive a redeploy: campaigns/, briefs/, images.
# Defaults to the repo root (unchanged local-dev behavior). In production this
# is set to a Railway Volume's mount path on the web service ONLY — Railway
# volumes cannot be shared between services, so anything reading/writing here
# must run inside that one service's container (subprocess is fine; a separate
# Railway service is not). See publish_scheduled_posts.py and server.py's
# /admin/publish-due for how the cron flow works around that.
# .resolve() matters here, not just cosmetic: agent_6 computes a path relative
# to PERSIST_DIR after calling .resolve() on the image path, so both sides
# need to go through symlinks the same way (e.g. macOS /tmp -> /private/tmp)
# or relative_to() raises even though the paths are the same location.
PERSIST_DIR = Path(os.getenv("PERSIST_DIR", str(PROJECT_ROOT))).resolve()

# Per-campaign output directory. Set CAMPAIGN_DIR env var before importing to
# isolate each brief's outputs. Falls back to PERSIST_DIR for legacy runs.
CAMPAIGN_DIR = Path(os.getenv("CAMPAIGN_DIR", str(PERSIST_DIR))).resolve()
IMAGES_DIR = CAMPAIGN_DIR / "images"
CSV_PATH = CAMPAIGN_DIR / "posts-queue.csv"
STATUS_PATH = CAMPAIGN_DIR / "pipeline-status.json"

# Ensure directories exist
CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API") or os.getenv("REPLICATE_API_TOKEN")

# Anthropic / Claude settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# Stable Diffusion settings
STABLE_DIFFUSION_MODEL = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024

# Campaign settings
CAMPAIGN_ID = os.getenv("CAMPAIGN_ID", "signal-sanctuary-ehs-awareness")
CAMPAIGN_BRIEF_PATH = Path(os.getenv("CAMPAIGN_BRIEF_PATH", str(PROJECT_ROOT / "Signal Sanctuary — EHS Awareness Campa.md")))

# Directory where frontend-generated JSON briefs are saved
BRIEFS_DIR = Path(os.getenv("BRIEFS_DIR", str(PERSIST_DIR / "briefs")))

# CSV column definitions
CSV_COLUMNS = [
    "post_id",
    "campaign_id",
    "content_pillar",
    "image_prompt",
    "overlay_text",      # Short, bold text ON the image (3-8 words)
    "caption",           # Post copy for Instagram text box
    "hashtags",          # Tags for Instagram text box (not on image)
    "image_status",
    "vision_status",
    "design_status",
    "facebook_status",
    "instagram_container_id",   # set once Agent 6 actually creates+publishes the container
    "scheduled_publish_at",     # ISO datetime a scheduled post becomes due; set by Agent 6, read by publish_scheduled_posts.py
]

# Status values
STATUS_PENDING = "pending"
STATUS_GENERATED = "generated"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_COMPLETE = "complete"
STATUS_READY = "ready"
STATUS_DRAFT_CREATED = "draft_created"  # unused for now — see agent_6_instagram_integration.py docstring
STATUS_SCHEDULED = "scheduled"          # queued, waiting for scheduled_publish_at (or a manual force-publish)
STATUS_PUBLISHED = "published"          # confirmed live on Instagram
STATUS_FAILED = "failed"

# Instagram Graph API settings
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IMAGE_HOST_BASE_URL = os.getenv("IMAGE_HOST_BASE_URL", "")
INSTAGRAM_SCHEDULE_DAYS_AHEAD = int(os.getenv("INSTAGRAM_SCHEDULE_DAYS_AHEAD", "7"))
