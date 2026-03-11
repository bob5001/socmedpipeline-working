"""
Agent 2: Image Generation via Replicate API
Reads posts-queue.csv and generates images for pending posts using Stable Diffusion.
"""

import csv
import sys
import os
import time
from pathlib import Path
import replicate
import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR,
    STABLE_DIFFUSION_MODEL, IMAGE_WIDTH, IMAGE_HEIGHT,
    STATUS_PENDING, STATUS_GENERATED, STATUS_FAILED,
    REPLICATE_API_TOKEN
)

# Set Replicate API token
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

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

def generate_image(prompt, post_id):
    """
    Generate image using Stable Diffusion via Replicate.
    Returns True if successful, False otherwise.
    """
    try:
        print(f"  Generating image for {post_id}...")
        print(f"  Prompt: {prompt[:80]}...")

        # Call Replicate API
        output = replicate.run(
            STABLE_DIFFUSION_MODEL,
            input={
                "prompt": prompt,
                "width": IMAGE_WIDTH,
                "height": IMAGE_HEIGHT,
                "num_outputs": 1,
                "guidance_scale": 7.5,
                "num_inference_steps": 50
            }
        )

        # Download image
        image_url = output[0] if isinstance(output, list) else output
        image_path = IMAGES_DIR / f"{post_id}.png"

        response = requests.get(image_url)
        response.raise_for_status()

        with open(image_path, 'wb') as f:
            f.write(response.content)

        print(f"  ✓ Saved to {image_path}")
        return True

    except Exception as e:
        print(f"  ✗ Error generating image: {e}")
        return False

def main():
    """Main execution."""
    print("Agent 2: Image Generation via Replicate API")
    print("=" * 50)

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Filter posts needing images
    pending_posts = [p for p in posts if p['image_status'] == STATUS_PENDING]
    print(f"Posts needing images: {len(pending_posts)}")

    if not pending_posts:
        print("No pending images. Nothing to do.")
        return

    # Generate images
    updated = False
    first = True
    for post in posts:
        if post['image_status'] == STATUS_PENDING:
            if not first:
                print("  Waiting 15s to avoid rate limit...")
                time.sleep(15)
            first = False
            success = generate_image(post['image_prompt'], post['post_id'])

            if success:
                post['image_status'] = STATUS_GENERATED
                updated = True
            else:
                post['image_status'] = STATUS_FAILED

    # Save updated CSV
    if updated:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with generation status")

    # Summary
    generated_count = sum(1 for p in posts if p['image_status'] == STATUS_GENERATED)
    print(f"\n✓ Task 2 complete. {generated_count}/{len(posts)} images generated.")
    print('  Suggested: git add posts-queue.csv images/ && git commit -m "Generated images for posts"')

if __name__ == "__main__":
    main()
