"""
Agent 6: Instagram Graph API Integration
Creates draft posts on the Instagram Business account for review before publishing.

NOTE on scheduling: Instagram's native auto-schedule feature (published=false +
scheduled_publish_time on container creation, so Meta publishes it for you later)
requires a whitelist grant from Meta that this app doesn't currently have —
confirmed via a live "(#3) User must be on whitelist" error. Plain container
creation without those params works fine, so this agent uses that instead:
it creates an unpublished container (a real draft) and stops. Someone must
explicitly call publish_draft_posts() (or POST /sessions/{id}/publish on the
server) to make it go live — Instagram containers expire after ~24 hours if
never published, so that has to happen same-day.
"""

import csv
import sys
from pathlib import Path
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR, PROJECT_ROOT,
    STATUS_READY, STATUS_DRAFT_CREATED, STATUS_SCHEDULED,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    IMAGE_HOST_BASE_URL,
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
    Create an Instagram media container. Left unpublished — this IS the draft.
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
    Publish a previously-created draft container, making it go live.
    Returns the published media id, or None on error (including expiry —
    Instagram drops unpublished containers after ~24 hours).
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

def create_instagram_draft(image_path, overlay_text, caption, hashtags):
    """
    Upload the image URL and create an unpublished draft container.
    Returns the container_id, or None on error.
    """
    full_caption = f"{caption}\n\n{hashtags}"

    print(f"  Image: {image_path.name}")
    print(f"  Overlay: {overlay_text}")
    print(f"  Caption: {caption[:60]}...")

    try:
        public_image_url = upload_to_image_host(image_path)
        print(f"  Image URL: {public_image_url[:60]}...")
    except Exception as e:
        print(f"  ✗ Error getting image URL: {e}")
        return None

    container_id = create_instagram_container(public_image_url, full_caption)
    if not container_id:
        return None

    print(f"  ✓ Draft container created: {container_id} (publish within ~24h before it expires)")
    return container_id

def publish_draft_posts():
    """
    Publish every post currently sitting as a draft (facebook_status ==
    STATUS_DRAFT_CREATED with a stored container_id). Called explicitly —
    by a human running this module with --publish-drafts, or by the server's
    POST /sessions/{id}/publish endpoint — never automatically.
    Returns (published_count, total_drafts).
    """
    posts = read_posts_csv()
    drafts = [p for p in posts if p['facebook_status'] == STATUS_DRAFT_CREATED and p.get('instagram_container_id')]

    if not drafts:
        print("No drafts ready to publish.")
        return 0, 0

    published_count = 0
    for post in posts:
        if post['facebook_status'] == STATUS_DRAFT_CREATED and post.get('instagram_container_id'):
            print(f"\n{post['post_id']} (container {post['instagram_container_id']})")
            media_id = publish_container(post['instagram_container_id'])
            if media_id:
                post['facebook_status'] = STATUS_SCHEDULED
                print(f"  ✓ Published (Media ID: {media_id})")
                published_count += 1
            else:
                print(f"  ✗ Failed to publish — container may have expired (~24h limit)")

    write_posts_csv(posts)
    return published_count, len(drafts)

def main():
    """Create draft containers for every post that's ready."""
    print("Agent 6: Instagram Graph API Integration")
    print("=" * 50)

    if not check_credentials():
        print("\n✗ Configuration incomplete. Please update .env with:")
        print("  - INSTAGRAM_BUSINESS_ACCOUNT_ID")
        print("  - INSTAGRAM_ACCESS_TOKEN")
        print("  - IMAGE_HOST_BASE_URL")
        print("\nSee README for setup instructions.")
        return

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Filter posts ready for Instagram
    ready_posts = [p for p in posts if p['facebook_status'] == STATUS_READY]
    print(f"Posts ready for Instagram: {len(ready_posts)}")

    if not ready_posts:
        print("No posts ready for Instagram. Complete pipeline first.")
        return

    draft_count = 0

    for post in posts:
        if post['facebook_status'] == STATUS_READY:
            image_path = IMAGES_DIR / f"{post['post_id']}-final.png"

            if not image_path.exists():
                print(f"✗ {post['post_id']}: Final image not found")
                continue

            print(f"\n{post['post_id']}")
            container_id = create_instagram_draft(
                image_path,
                post['overlay_text'],
                post['caption'],
                post['hashtags']
            )

            if container_id:
                post['facebook_status'] = STATUS_DRAFT_CREATED
                post['instagram_container_id'] = container_id
                draft_count += 1
            else:
                print(f"  ✗ Failed to create draft")

    if draft_count > 0:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with draft status")

    print(f"\n✓ Task 6 complete.")
    print(f"  Drafts created: {draft_count}/{len(ready_posts)}")

    if draft_count > 0:
        print(f"\n✓✓ PIPELINE COMPLETE")
        print(f"  {draft_count} draft(s) created on Instagram Business account — NOT yet live")
        print(f"  Publish within ~24h (containers expire after that) via publish_draft_posts()")
        print(f"  or POST /sessions/<id>/publish, or discard by simply not publishing.")
        print('  Suggested: git add posts-queue.csv && git commit -m "Created Instagram drafts"')

if __name__ == "__main__":
    if "--publish-drafts" in sys.argv:
        published, total = publish_draft_posts()
        print(f"\n✓ Published {published}/{total} drafts")
    else:
        main()
