"""
Agent 6: Instagram Graph API Integration
Schedules posts to Instagram Business accounts using the official API.
Posts are scheduled for future publishing (default: 7 days ahead) for review.
"""

import csv
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR, PROJECT_ROOT,
    STATUS_READY, STATUS_SCHEDULED,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    IMAGE_HOST_BASE_URL,
    INSTAGRAM_SCHEDULE_DAYS_AHEAD
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

def create_instagram_container(image_url, caption, scheduled_publish_time=None):
    """
    Step 1: Create Instagram media container.

    Scheduling happens HERE, not on the publish call: pass scheduled_publish_time
    (a Unix timestamp, 10 minutes to 75 days out) and Instagram creates the
    container as unpublished and auto-publishes it server-side at that time —
    no follow-up call needed. `/media_publish` does not accept
    scheduled_publish_time at all; passing it there is silently ignored and the
    container publishes immediately, which is the bug this replaced.

    Returns container_id or None on error.
    """
    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"

    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    if scheduled_publish_time is not None:
        params["published"] = "false"
        params["scheduled_publish_time"] = scheduled_publish_time

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
    Immediately publish a container that was created WITHOUT a schedule.
    Only used when INSTAGRAM_SCHEDULE_DAYS_AHEAD is 0 (publish now, no review
    window). Scheduled containers publish themselves — never call this on one.
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

def create_scheduled_instagram_post(post_id, image_path, overlay_text, caption, hashtags):
    """
    Full workflow: upload image, create container (scheduled or immediate).
    Returns the scheduled container's id, or the published media's id if
    INSTAGRAM_SCHEDULE_DAYS_AHEAD is 0.
    """
    # Combine caption and hashtags for Instagram
    full_caption = f"{caption}\n\n{hashtags}"

    print(f"  Image: {image_path.name}")
    print(f"  Overlay: {overlay_text}")
    print(f"  Caption: {caption[:60]}...")

    # Step 1: Get public URL for image
    try:
        public_image_url = upload_to_image_host(image_path)
        print(f"  Image URL: {public_image_url[:60]}...")
    except Exception as e:
        print(f"  ✗ Error getting image URL: {e}")
        return None

    if INSTAGRAM_SCHEDULE_DAYS_AHEAD > 0:
        # Scheduled: pass the timestamp at container creation; Instagram
        # publishes it automatically later. No media_publish call.
        schedule_time = datetime.now() + timedelta(days=INSTAGRAM_SCHEDULE_DAYS_AHEAD)
        container_id = create_instagram_container(
            public_image_url, full_caption, scheduled_publish_time=int(schedule_time.timestamp())
        )
        if not container_id:
            return None

        schedule_date = schedule_time.strftime("%Y-%m-%d %H:%M")
        print(f"  ✓ Container created and scheduled for {schedule_date} (id: {container_id})")
        return container_id
    else:
        # Publish now: create an unscheduled container, then publish it.
        container_id = create_instagram_container(public_image_url, full_caption)
        if not container_id:
            return None

        print(f"  ✓ Container created: {container_id}")
        time.sleep(1)  # brief delay between API calls

        media_id = publish_container(container_id)
        if not media_id:
            return None

        print(f"  ✓ Published immediately (Media ID: {media_id})")
        return media_id

def main():
    """Main execution."""
    print("Agent 6: Instagram Graph API Integration")
    print("=" * 50)

    # Check credentials
    if not check_credentials():
        print("\n✗ Configuration incomplete. Please update .env with:")
        print("  - INSTAGRAM_BUSINESS_ACCOUNT_ID")
        print("  - INSTAGRAM_ACCESS_TOKEN")
        print("  - IMAGE_HOST_BASE_URL")
        print("\nSee README for setup instructions.")
        return

    print(f"Schedule settings: {INSTAGRAM_SCHEDULE_DAYS_AHEAD} days ahead")
    print()

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Filter posts ready for Instagram
    ready_posts = [p for p in posts if p['facebook_status'] == STATUS_READY]
    print(f"Posts ready for Instagram: {len(ready_posts)}")

    if not ready_posts:
        print("No posts ready for Instagram. Complete pipeline first.")
        return

    # Schedule posts
    scheduled_count = 0

    for post in posts:
        if post['facebook_status'] == STATUS_READY:
            image_path = IMAGES_DIR / f"{post['post_id']}-final.png"

            if not image_path.exists():
                print(f"✗ {post['post_id']}: Final image not found")
                continue

            print(f"\n{post['post_id']}")
            # Returns a scheduled container's id, or a published media's id if
            # INSTAGRAM_SCHEDULE_DAYS_AHEAD is 0 — create_scheduled_instagram_post
            # already printed which one happened.
            result_id = create_scheduled_instagram_post(
                post['post_id'],
                image_path,
                post['overlay_text'],
                post['caption'],
                post['hashtags']
            )

            if result_id:
                post['facebook_status'] = STATUS_SCHEDULED
                scheduled_count += 1
            else:
                print(f"  ✗ Failed to schedule")

    # Save updated CSV
    if scheduled_count > 0:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with scheduled status")

    # Summary
    print(f"\n✓ Task 6 complete.")
    print(f"  Posts scheduled: {scheduled_count}/{len(ready_posts)}")

    if scheduled_count > 0:
        schedule_date = (datetime.now() + timedelta(days=INSTAGRAM_SCHEDULE_DAYS_AHEAD)).strftime("%Y-%m-%d")
        print(f"  Scheduled publish date: {schedule_date}")
        print(f"\n✓✓ PIPELINE COMPLETE")
        print(f"  {scheduled_count} posts scheduled on Instagram Business account")
        print(f"  Review and manage at: https://business.facebook.com/creatorstudio")
        print('  Suggested: git add posts-queue.csv && git commit -m "Scheduled posts on Instagram"')

if __name__ == "__main__":
    main()
