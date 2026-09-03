"""
Agent 6: Instagram Graph API Integration
Queues posts for future publishing on the Instagram Business account.

NOTE on scheduling: Instagram's native auto-schedule feature (published=false +
scheduled_publish_time on container creation, so Meta publishes it for you
later) requires a whitelist grant from Meta that this app doesn't currently
have — confirmed via a live "(#3) User must be on whitelist" error. Creating
an unpublished container without that whitelist also isn't a real substitute:
those containers expire after ~24 hours, too short a review window.

So scheduling is handled entirely on our side instead: this agent does NOT
call the Instagram API when a post becomes ready. It just records a target
time (INSTAGRAM_SCHEDULE_DAYS_AHEAD days out) and stops — facebook_status
becomes STATUS_SCHEDULED with scheduled_publish_at set, no container exists
yet. publish_scheduled_posts.py (run periodically by a Railway Cron Job
service, across every campaign) creates the container AND publishes it in one
step, but only once that target time has arrived — so there's no expiry clock
running while a post waits. publish_due_posts() below is the same idea
scoped to one campaign, for manual/local use or the server's
POST /sessions/{id}/publish endpoint (which force-publishes immediately,
skipping the scheduled_publish_at check).
"""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR, PROJECT_ROOT,
    STATUS_READY, STATUS_SCHEDULED, STATUS_PUBLISHED, STATUS_FAILED,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    IMAGE_HOST_BASE_URL,
    INSTAGRAM_SCHEDULE_DAYS_AHEAD,
)

def read_posts_csv():
    """Read posts from CSV."""
    posts = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        posts = list(reader)
    return posts

def write_posts_csv(posts):
    """Write updated posts to CSV."""
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(posts)

def check_credentials():
    """Verify Instagram API credentials are configured."""
    if not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        print("✗ Missing INSTAGRAM_BUSINESS_ACCOUNT_ID in .env")
        return False
    if not INSTAGRAM_ACCESS_TOKEN:
        print("✗ Missing INSTAGRAM_ACCESS_TOKEN in .env")
        return False
    if not IMAGE_HOST_BASE_URL or IMAGE_HOST_BASE_URL.startswith("TODO_") or "your-image-host" in IMAGE_HOST_BASE_URL:
        print("✗ IMAGE_HOST_BASE_URL is missing or still a placeholder in .env")
        print("  Instagram API requires publicly accessible image URLs")
        return False
    return True

def upload_to_image_host(local_path):
    """
    Return a public URL for a locally generated image.

    Images aren't uploaded anywhere separately — server.py mounts each campaign's
    images/ dir as static files at /campaigns/<session_id>/images/<file>. So the
    public URL is just IMAGE_HOST_BASE_URL (the deployed Railway backend's root)
    plus the image's path relative to the project root. Keep this in sync with
    the StaticFiles mount in server.py if either one changes.
    """
    relative_path = local_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    public_url = f"{IMAGE_HOST_BASE_URL.rstrip('/')}/{relative_path}"
    return public_url

def create_instagram_container(image_url, caption):
    """
    Create an Instagram media container.
    Returns container_id or None on error.
    """
    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"

    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    try:
        response = requests.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "id" in data:
            return data["id"]
        else:
            print(f"  ✗ No container ID in response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error creating container: {e}")
        if hasattr(e.response, 'text'):
            print(f"    Response: {e.response.text}")
        return None

def publish_container(container_id):
    """
    Publish a container, making it go live immediately.
    Returns the published media id, or None on error.
    """
    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"

    params = {
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    try:
        response = requests.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "id" in data:
            return data["id"]
        else:
            print(f"  ✗ No media ID in response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error publishing container: {e}")
        if hasattr(e.response, 'text'):
            print(f"    Response: {e.response.text}")
        return None

def publish_post_row(row: dict, images_dir: Path) -> bool:
    """
    Create a container and immediately publish it for one CSV row. Mutates
    row in place: sets facebook_status to STATUS_PUBLISHED or STATUS_FAILED,
    and instagram_container_id on success.

    Shared by publish_due_posts() (single campaign) and
    publish_scheduled_posts.py (the cron sweep across every campaign) — the
    only two places that should ever actually call the Instagram API to
    publish something.
    """
    image_path = images_dir / f"{row['post_id']}-final.png"
    if not image_path.exists():
        print(f"  ✗ {row['post_id']}: final image not found at {image_path}")
        row['facebook_status'] = STATUS_FAILED
        return False

    full_caption = f"{row['caption']}\n\n{row['hashtags']}"

    try:
        public_url = upload_to_image_host(image_path)
    except Exception as e:
        print(f"  ✗ {row['post_id']}: error getting image URL: {e}")
        row['facebook_status'] = STATUS_FAILED
        return False

    container_id = create_instagram_container(public_url, full_caption)
    if not container_id:
        row['facebook_status'] = STATUS_FAILED
        return False

    media_id = publish_container(container_id)
    if not media_id:
        row['facebook_status'] = STATUS_FAILED
        return False

    row['facebook_status'] = STATUS_PUBLISHED
    row['instagram_container_id'] = container_id
    print(f"  ✓ {row['post_id']}: published (Media ID: {media_id})")
    return True

def publish_due_posts(force: bool = False):
    """
    Publish posts in THIS campaign (config.settings.CSV_PATH — set CAMPAIGN_DIR
    before importing this module to target a specific one) whose scheduled
    time has arrived. force=True ignores scheduled_publish_at and publishes
    every STATUS_SCHEDULED post immediately — used for a manual "publish now"
    override, e.g. via POST /sessions/{id}/publish.
    Returns (published_count, checked_count).
    """
    posts = read_posts_csv()
    now = datetime.now()
    due = []
    for row in posts:
        if row.get('facebook_status') != STATUS_SCHEDULED:
            continue
        if force:
            due.append(row)
            continue
        target = row.get('scheduled_publish_at', '')
        try:
            if target and datetime.fromisoformat(target) <= now:
                due.append(row)
        except ValueError:
            continue

    if not due:
        print("No due posts to publish.")
        return 0, 0

    published_count = 0
    for row in due:
        print(f"\n{row['post_id']}")
        if publish_post_row(row, IMAGES_DIR):
            published_count += 1

    write_posts_csv(posts)
    return published_count, len(due)

def main():
    """Queue every ready post with a target publish time. No API calls here —
    see the module docstring for why publishing is deferred to a cron sweep."""
    print("Agent 6: Instagram Graph API Integration")
    print("=" * 50)

    if not check_credentials():
        print("\n✗ Configuration incomplete. Please update .env with:")
        print("  - INSTAGRAM_BUSINESS_ACCOUNT_ID")
        print("  - INSTAGRAM_ACCESS_TOKEN")
        print("  - IMAGE_HOST_BASE_URL")
        print("\nSee README for setup instructions.")
        return

    print(f"Schedule settings: {INSTAGRAM_SCHEDULE_DAYS_AHEAD} days ahead")
    print()

    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    ready_posts = [p for p in posts if p['facebook_status'] == STATUS_READY]
    print(f"Posts ready for Instagram: {len(ready_posts)}")

    if not ready_posts:
        print("No posts ready for Instagram. Complete pipeline first.")
        return

    queued_count = 0

    for post in posts:
        if post['facebook_status'] == STATUS_READY:
            image_path = IMAGES_DIR / f"{post['post_id']}-final.png"

            if not image_path.exists():
                print(f"✗ {post['post_id']}: Final image not found")
                continue

            target_time = datetime.now() + timedelta(days=INSTAGRAM_SCHEDULE_DAYS_AHEAD)
            post['facebook_status'] = STATUS_SCHEDULED
            post['scheduled_publish_at'] = target_time.isoformat()
            print(f"{post['post_id']}: queued for {target_time.strftime('%Y-%m-%d %H:%M')}")
            queued_count += 1

    if queued_count > 0:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with scheduled status")

    print(f"\n✓ Task 6 complete.")
    print(f"  Posts queued: {queued_count}/{len(ready_posts)}")

    if queued_count > 0:
        print(f"\n✓✓ PIPELINE COMPLETE")
        print(f"  {queued_count} post(s) queued — no Instagram API calls made yet.")
        print(f"  publish_scheduled_posts.py (run by Railway Cron) publishes each")
        print(f"  one automatically once its scheduled_publish_at arrives.")
        print('  Suggested: git add posts-queue.csv && git commit -m "Queued posts for Instagram"')

if __name__ == "__main__":
    if "--publish-due" in sys.argv:
        published, checked = publish_due_posts(force=False)
        print(f"\n✓ Published {published}/{checked} due posts")
    elif "--publish-now" in sys.argv:
        published, checked = publish_due_posts(force=True)
        print(f"\n✓ Published {published}/{checked} scheduled posts")
    else:
        main()
