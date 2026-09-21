#!/usr/bin/env python3
"""
FastAPI server — session init and status for the social media pipeline.

Auth: every endpoint except /health and the image route below requires an
`X-API-Key` header matching the PIPELINE_API_KEY env var (fail-closed: if the env
var is unset, protected endpoints return 503 rather than running open). Callers:
the frontend's server-side route (app/api/brief/[id]/route.ts) and the cron
trigger (trigger_publish.py) — both must have PIPELINE_API_KEY set. No CORS: no
browser calls this directly. The Swagger UI / OpenAPI schema are disabled.

Endpoints:
  POST /sessions          Accept a brief JSON body, create campaign dir, launch pipeline
  GET  /sessions/{id}     Return campaign status
  GET  /sessions/{id}/log Return pipeline stdout log
  POST /sessions/{id}/publish  Force-publish that session's queued posts immediately,
                           skipping their scheduled_publish_at time — a manual override.
  POST /admin/publish-due Sweep every campaign for posts whose scheduled_publish_at has
                           arrived and publish them. This is the real cron endpoint: a
                           separate Railway Cron Job service can't touch this service's
                           files directly (Railway volumes aren't shareable across
                           services), so it just calls this over HTTP instead — see
                           trigger_publish.py and publish_scheduled_posts.py.
  GET  /health            Liveness check (public)
  GET  /campaigns/{id}/images/{file}
                          PUBLIC, image files only (Agent 6 / Instagram needs a publicly
                           reachable URL for each final image; see IMAGE_HOST_BASE_URL in
                           .env and agent_6_instagram_integration.py). Nothing else under a
                           campaign dir (CSV, logs, status) is served.

Persistence: PROJECT_ROOT is the repo checkout (ephemeral — wiped on every
redeploy). BRIEFS_DIR/CAMPAIGNS_DIR live under PERSIST_DIR instead, which in
production is a Railway Volume mounted on this service only (env var
PERSIST_DIR, e.g. /data) so campaign data survives redeploys. Defaults to
PROJECT_ROOT for local dev, where redeploys aren't a concern.
"""

import asyncio
import csv
import hmac
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()  # local dev; on Railway real env vars win (load_dotenv never overrides them)

PROJECT_ROOT = Path(__file__).parent
PERSIST_DIR = Path(os.getenv("PERSIST_DIR", str(PROJECT_ROOT)))
BRIEFS_DIR = PERSIST_DIR / "briefs"
CAMPAIGNS_DIR = PERSIST_DIR / "campaigns"

BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Social Media Pipeline API", version="0.1.0",
    docs_url=None, redoc_url=None, openapi_url=None,  # don't advertise the API surface
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Shared-secret check. Reads the env var per request; fails closed if it's unset."""
    expected = os.getenv("PIPELINE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Server auth is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


_AUTH = [Depends(require_api_key)]

# Session ids become directory/file names (CAMPAIGNS_DIR / id, brief-<id>.json), so they must
# not be able to contain "/" or start with "." — this rules out "..", absolute paths, etc.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_IMAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(png|jpe?g)$", re.IGNORECASE)


def _check_session_id(session_id: str) -> str:
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise HTTPException(status_code=422, detail="Invalid session id")
    return session_id


# Public image route: Instagram must be able to fetch each final image by URL, so this one
# route is unauthenticated — but it serves ONLY image files from <campaign>/images/, never
# the rest of the campaign dir. Agent 6 builds URLs as IMAGE_HOST_BASE_URL + the image's path
# relative to PERSIST_DIR (see upload_to_image_host in agent_6_instagram_integration.py), so
# this path shape and that URL construction must stay in sync. HEAD is allowed because some
# fetchers probe with it (the old StaticFiles mount answered HEAD too).
@app.api_route("/campaigns/{session_id}/images/{filename}", methods=["GET", "HEAD"])
async def campaign_image(session_id: str, filename: str):
    images_root = (CAMPAIGNS_DIR / _check_session_id(session_id) / "images").resolve()
    if not _IMAGE_NAME_RE.fullmatch(filename):
        raise HTTPException(status_code=404, detail="Not found")
    path = (images_root / filename).resolve()
    if images_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


# Kept in sync with config.settings.CSV_COLUMNS by hand — this module writes
# the CSV before any agent (which import settings) has run.
_CSV_COLUMNS = [
    "post_id", "campaign_id", "content_pillar", "image_prompt",
    "overlay_text", "caption", "hashtags",
    "image_status", "vision_status", "design_status", "facebook_status",
    "instagram_container_id", "scheduled_publish_at",
]


class SessionPayload(BaseModel):
    brief: dict[str, Any]
    posts: list[dict[str, Any]] | None = None


@app.post("/sessions", status_code=201, dependencies=_AUTH)
async def create_session(payload: SessionPayload, background_tasks: BackgroundTasks):
    brief = payload.brief

    if not brief.get("id"):
        brief["id"] = datetime.now().strftime("session-%Y%m%d-%H%M%S")

    session_id = _check_session_id(str(brief["id"]))
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
            "scheduled_publish_at": "",
        })
    csv_path = campaign_dir / "posts-queue.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@app.get("/sessions/{session_id}", dependencies=_AUTH)
async def get_session(session_id: str):
    campaign_dir = CAMPAIGNS_DIR / _check_session_id(session_id)
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    status_file = campaign_dir / "pipeline-status.json"
    if not status_file.exists():
        return {"session_id": session_id, "status": "initializing"}

    return json.loads(status_file.read_text())


@app.get("/sessions/{session_id}/log", dependencies=_AUTH)
async def get_log(session_id: str):
    log_path = CAMPAIGNS_DIR / _check_session_id(session_id) / "pipeline.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="No log yet")
    return {"log": log_path.read_text(errors="replace")}


@app.post("/sessions/{session_id}/publish", dependencies=_AUTH)
async def publish_session(session_id: str):
    """
    Force-publish this session's queued posts (facebook_status == scheduled)
    right now, ignoring their scheduled_publish_at time — a manual "publish
    now instead of waiting" override. Normal scheduled publishing happens on
    its own via POST /admin/publish-due (see that endpoint). Runs
    synchronously since it's a small number of API calls, not a full
    pipeline pass.
    """
    campaign_dir = CAMPAIGNS_DIR / _check_session_id(session_id)
    if not campaign_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(PROJECT_ROOT / "src" / "agent_6_instagram_integration.py"),
        "--publish-now",
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "CAMPAIGN_DIR": str(campaign_dir)},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")

    (campaign_dir / "publish.log").write_text(output)

    return {"session_id": session_id, "output": output}


@app.post("/admin/publish-due", dependencies=_AUTH)
async def publish_due():
    """
    Sweep every campaign under CAMPAIGNS_DIR for posts whose
    scheduled_publish_at has arrived and publish them. This is what a
    periodic trigger should call — intended to be hit by a separate Railway
    Cron Job service running trigger_publish.py, since that service can't
    share this one's Volume and must go through HTTP instead. Runs as a
    subprocess of THIS service/container, so it sees the same mounted
    PERSIST_DIR this process does.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(PROJECT_ROOT / "publish_scheduled_posts.py"),
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")
    return {"output": output}


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
