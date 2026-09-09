#!/usr/bin/env python3
"""
Publish every post, across every campaign, whose scheduled time has arrived.

Run this by calling POST /admin/publish-due on the deployed web service, not
by deploying it as its own Railway service. Railway volumes can't be shared
between services (confirmed with Railway support — their own recommendation
for cross-service shared state is external object storage, not volumes), and
campaign data lives on a Volume mounted on the web service only. A separate
Cron Job service running this script directly would see an empty, unmounted
filesystem — nothing to publish, ever. trigger_publish.py is what the actual
Railway Cron Job service runs instead: it just POSTs to /admin/publish-due,
and this script executes as a subprocess of the web service's own container
(server.py's publish_due() handler), so it shares that process's mounted
PERSIST_DIR. Still directly runnable locally for manual testing.

Runs as a single pass over campaigns/*/posts-queue.csv rather than going
through Agent 6's normal per-campaign config (config.settings.CAMPAIGN_DIR is
fixed at import time, so it can only ever point at one campaign per process —
not usable here since a cron sweep needs to check all of them in one run).
Reuses Agent 6's lower-level helpers directly since those don't depend on
CAMPAIGN_DIR — see agent_6_instagram_integration.py's module docstring for why
publishing is deferred to this script instead of scheduled at container-
creation time.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from config.settings import PERSIST_DIR, CSV_COLUMNS, STATUS_SCHEDULED
from src.agent_6_instagram_integration import check_credentials, publish_post_row

CAMPAIGNS_DIR = PERSIST_DIR / "campaigns"

def process_campaign_csv(csv_path: Path) -> int:
    """Publish due posts in one campaign's CSV. Returns count published."""
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    images_dir = csv_path.parent / "images"
    now = datetime.now()
    published = 0
    changed = False

    for row in rows:
        if row.get('facebook_status') != STATUS_SCHEDULED:
            continue

        target = row.get('scheduled_publish_at', '')
        if not target:
            continue
        try:
            target_dt = datetime.fromisoformat(target)
        except ValueError:
            print(f"  ✗ {row['post_id']}: unparseable scheduled_publish_at {target!r}, skipping")
            continue
        if target_dt > now:
            continue  # not due yet

        print(f"\n{csv_path.parent.name}/{row['post_id']} (due {target})")
        if publish_post_row(row, images_dir):
            published += 1
        changed = True

    if changed:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    return published

def main():
    print("publish_scheduled_posts: sweeping all campaigns for due posts")
    print("=" * 60)

    if not check_credentials():
        print("✗ Instagram credentials not configured — skipping this run.")
        return

    if not CAMPAIGNS_DIR.exists():
        print("No campaigns directory found — nothing to do.")
        return

    csv_paths = sorted(CAMPAIGNS_DIR.glob("*/posts-queue.csv"))
    print(f"Found {len(csv_paths)} campaign(s) to check")

    total_published = 0
    for csv_path in csv_paths:
        total_published += process_campaign_csv(csv_path)

    print(f"\n✓ Published {total_published} due post(s) across all campaigns.")

if __name__ == "__main__":
    main()
