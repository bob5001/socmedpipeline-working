"""Configuration settings for the social media pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
IMAGES_DIR = PROJECT_ROOT / "images"
CSV_PATH = PROJECT_ROOT / "posts-queue.csv"
STATUS_PATH = PROJECT_ROOT / "pipeline-status.json"

# Ensure directories exist
IMAGES_DIR.mkdir(exist_ok=True)

# API Keys
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API") or os.getenv("REPLICATE_API_TOKEN")

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_VISION_MODEL = "llava:7b"
OLLAMA_TEXT_MODEL = "llama3.1:8b"

# Stable Diffusion settings
STABLE_DIFFUSION_MODEL = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024

# Campaign settings
CAMPAIGN_ID = "signal-sanctuary-ehs-awareness"
CAMPAIGN_BRIEF_PATH = PROJECT_ROOT / "Signal Sanctuary — EHS Awareness Campa.md"

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
    "facebook_status"
]

# Status values
STATUS_PENDING = "pending"
STATUS_GENERATED = "generated"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_COMPLETE = "complete"
STATUS_READY = "ready"
STATUS_DRAFT_CREATED = "draft_created"
STATUS_SCHEDULED = "scheduled"
STATUS_FAILED = "failed"

# Instagram Graph API settings
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IMAGE_HOST_BASE_URL = os.getenv("IMAGE_HOST_BASE_URL", "")
INSTAGRAM_SCHEDULE_DAYS_AHEAD = int(os.getenv("INSTAGRAM_SCHEDULE_DAYS_AHEAD", "7"))
