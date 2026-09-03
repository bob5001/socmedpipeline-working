#!/usr/bin/env python3
"""
FastAPI server — session init and status for the social media pipeline.

Endpoints:
  POST /sessions          Accept a brief JSON body, create campaign dir, launch pipeline
  GET  /sessions/{id}     Return campaign status
  GET  /sessions/{id}/log Return pipeline stdout log
  POST /sessions/{id}/publish  Publish that session's Instagram drafts (Agent 6 creates
                           unpublished containers, not live posts — this is the explicit
                           step that makes them go live; containers expire after ~24h)
  GET  /health            Liveness check
  GET  /campaigns/...     Static file serving for generated images (Agent 6 / Instagram
                           needs a publicly reachable URL for each final image; see
                           IMAGE_HOST_BASE_URL in .env and agent_6_instagram_integration.py)
"""

import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Serves every campaign's images/ dir publicly at /campaigns/<session_id>/images/<file>.
# Agent 6 builds Instagram image URLs as IMAGE_HOST_BASE_URL + that same relative path
# (see upload_to_image_host in agent_6_instagram_integration.py), so this mount and that
# URL construction must stay in sync.
app.mount("/campaigns", StaticFiles(directory=CAMPAIGNS_DIR), name="campaign-images")


# Kept in sync with config.settings.CSV_COLUMNS by hand — this module writes
# the CSV before any agent (which import settings) has run.
_CSV_COLUMNS = [
    "post_id", "campaign_id", "content_pillar", "image_prompt",
    "overlay_text", "caption", "hashtags",
    "image_status", "vision_status", "design_status", "facebook_status",
    "instagram_container_id",
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
            "instagram_container_id": "",
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


@app.post("/sessions/{session_id}/publish")
async def publish_session(session_id: str):
    """
    Publish that session's Instagram drafts (facebook_status == draft_created).
    Agent 6 only ever creates unpublished containers — nothing goes live until
    this is called explicitly. Runs synchronously since it's a small number of
    API calls, not a full pipeline pass.
    """
    campaign_dir = CAMPAIGNS_DIR / session_id
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(PROJECT_ROOT / "src" / "agent_6_instagram_integration.py"),
        "--publish-drafts",
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "CAMPAIGN_DIR": str(campaign_dir)},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")

    (campaign_dir / "publish.log").write_text(output)

    return {"session_id": session_id, "output": output}


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
