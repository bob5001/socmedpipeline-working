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

def create_instagram_container(image_url, caption):
    """
    Step 1: Create Instagram media container.
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

def schedule_instagram_publish(container_id, days_ahead=7):
    """
    Step 2: Schedule (or immediately publish) the media container.
    Returns True on success, False on error.
    """
    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"

    # Calculate future timestamp (days ahead for review)
    schedule_time = datetime.now() + timedelta(days=days_ahead)
    unix_timestamp = int(schedule_time.timestamp())

    params = {
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    # Schedule for future (between 10 minutes and 75 days from now)
    if days_ahead > 0:
        params["scheduled_publish_time"] = unix_timestamp

    try:
        response = requests.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "id" in data:
            schedule_date = schedule_time.strftime("%Y-%m-%d %H:%M")
            print(f"  ✓ Scheduled for {schedule_date}")
            return data["id"]
        else:
            print(f"  ✗ No media ID in response: {data}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error scheduling publish: {e}")
        if hasattr(e.response, 'text'):
            print(f"    Response: {e.response.text}")
        return None

def create_scheduled_instagram_post(post_id, image_path, overlay_text, caption, hashtags):
    """
    Full workflow: Upload image, create container, schedule publish.
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

    # Step 2: Create media container
    container_id = create_instagram_container(public_image_url, full_caption)
    if not container_id:
        return None

    print(f"  ✓ Container created: {container_id}")

    # Brief delay between API calls
    time.sleep(1)

    # Step 3: Schedule publish
    media_id = schedule_instagram_publish(container_id, INSTAGRAM_SCHEDULE_DAYS_AHEAD)
    if not media_id:
        return None

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
            media_id = create_scheduled_instagram_post(
                post['post_id'],
                image_path,
                post['overlay_text'],
                post['caption'],
                post['hashtags']
            )

            if media_id:
                post['facebook_status'] = STATUS_SCHEDULED
                print(f"  ✓ Scheduled (Media ID: {media_id})")
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
