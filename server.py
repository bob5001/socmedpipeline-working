#!/usr/bin/env python3
"""
FastAPI server — session init and status for the social media pipeline.

Endpoints:
  POST /sessions          Accept a brief JSON body, create campaign dir, launch pipeline
  GET  /sessions/{id}     Return campaign status
  GET  /sessions/{id}/log Return pipeline stdout log
  GET  /health            Liveness check
"""

import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent
BRIEFS_DIR = PROJECT_ROOT / "briefs"
CAMPAIGNS_DIR = PROJECT_ROOT / "campaigns"

BRIEFS_DIR.mkdir(exist_ok=True)
CAMPAIGNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Social Media Pipeline API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_CSV_COLUMNS = [
    "post_id", "campaign_id", "content_pillar", "image_prompt",
    "overlay_text", "caption", "hashtags",
    "image_status", "vision_status", "design_status", "facebook_status",
]


class SessionPayload(BaseModel):
    brief: dict[str, Any]
    posts: list[dict[str, Any]] | None = None


@app.post("/sessions", status_code=201)
async def create_session(payload: SessionPayload, background_tasks: BackgroundTasks):
    brief = payload.brief

    if not brief.get("id"):
        brief["id"] = datetime.now().strftime("session-%Y%m%d-%H%M%S")

    session_id = brief["id"]
    brief_path = BRIEFS_DIR / f"brief-{session_id}.json"
    brief_path.write_text(json.dumps(brief, indent=2))

    campaign_dir = CAMPAIGNS_DIR / session_id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    from_agent = 1
    if payload.posts:
        _write_posts_csv(campaign_dir, brief, payload.posts)
        from_agent = 2

    background_tasks.add_task(_run_pipeline, brief_path, session_id, from_agent)

    return {
        "session_id": session_id,
        "campaign_dir": str(campaign_dir),
        "status_url": f"/sessions/{session_id}",
        "from_agent": from_agent,
    }


def _write_posts_csv(campaign_dir: Path, brief: dict, posts: list[dict]) -> None:
    campaign_id = brief.get("business_name", "campaign").lower().replace(" ", "-")
    rows = []
    for post in posts:
        hashtags = post.get("hashtags", [])
        if isinstance(hashtags, list):
            hashtags = " ".join(hashtags)
        rows.append({
            "post_id": f"P-{datetime.now().strftime('%Y%m%d-%H%M%S%f')}",
            "campaign_id": campaign_id,
            "content_pillar": post.get("content_pillar", post.get("platform", "general")),
            "image_prompt": post.get("image_prompt", ""),
            "overlay_text": post.get("overlay_text", ""),
            "caption": post.get("caption", ""),
            "hashtags": hashtags,
            "image_status": "pending",
            "vision_status": "pending",
            "design_status": "pending",
            "facebook_status": "pending",
        })
    csv_path = campaign_dir / "posts-queue.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    campaign_dir = CAMPAIGNS_DIR / session_id
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    status_file = campaign_dir / "pipeline-status.json"
    if not status_file.exists():
        return {"session_id": session_id, "status": "initializing"}

    return json.loads(status_file.read_text())


@app.get("/sessions/{session_id}/log")
async def get_log(session_id: str):
    log_path = CAMPAIGNS_DIR / session_id / "pipeline.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="No log yet")
    return {"log": log_path.read_text(errors="replace")}


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _run_pipeline(brief_path: Path, session_id: str, from_agent: int = 1):
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(PROJECT_ROOT / "run_pipeline.py"),
        "--brief", str(brief_path),
        "--auto",
        "--from-agent", str(from_agent),
        cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    log_path = CAMPAIGNS_DIR / session_id / "pipeline.log"
    log_path.write_bytes(stdout)
