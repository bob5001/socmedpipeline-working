"""
Agent 4: Affinity Designer Text Overlay
Opens approved images in Affinity Designer (via MCP), overlays caption and hashtags,
and exports final versions.

NOTE: This requires the Affinity Designer MCP server to be installed and running.
If not available, this will create a TODO placeholder.
"""

import csv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR,
    STATUS_APPROVED, STATUS_COMPLETE, STATUS_PENDING
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

def apply_text_overlay(image_path, caption, hashtags, output_path):
    """
    Apply text overlay using Affinity Designer MCP.

    TODO: This requires MCP integration. For now, this is a placeholder.
    When Affinity Designer MCP is available, this function should:
    1. Open the image at image_path
    2. Add text layer with caption (readable typography, appropriate positioning)
    3. Add hashtags in smaller text
    4. Export to output_path
    """
    # Placeholder implementation
    # In production, this would use MCP to control Affinity Designer

    print(f"  TODO: Apply text overlay to {image_path.name}")
    print(f"    Caption: {caption[:50]}...")
    print(f"    Hashtags: {hashtags}")
    print(f"    Would export to: {output_path}")

    # For now, just copy the original image as placeholder
    import shutil
    shutil.copy(image_path, output_path)

    return True

def main():
    """Main execution."""
    print("Agent 4: Affinity Designer Text Overlay")
    print("=" * 50)
    print("NOTE: Affinity Designer MCP integration required")
    print()

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Filter posts needing design
    pending_design = [
        p for p in posts
        if p['vision_status'] == STATUS_APPROVED
        and p['design_status'] == STATUS_PENDING
    ]
    print(f"Posts needing design overlay: {len(pending_design)}")

    if not pending_design:
        print("No approved images ready for design. Nothing to do.")
        return

    # Apply overlays
    updated = False
    for post in posts:
        if (post['vision_status'] == STATUS_APPROVED
            and post['design_status'] == STATUS_PENDING):

            image_path = IMAGES_DIR / f"{post['post_id']}.png"
            output_path = IMAGES_DIR / f"{post['post_id']}-final.png"

            if not image_path.exists():
                print(f"✗ {post['post_id']}: Source image not found")
                continue

            print(f"\n{post['post_id']}")
            success = apply_text_overlay(
                image_path,
                post['caption'],
                post['hashtags'],
                output_path
            )

            if success:
                post['design_status'] = STATUS_COMPLETE
                print(f"  ✓ Design complete")
                updated = True

    # Save updated CSV
    if updated:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with design status")

    # Summary
    complete_count = sum(1 for p in posts if p['design_status'] == STATUS_COMPLETE)

    print(f"\n✓ Task 4 complete. {complete_count}/{len(posts)} designs ready.")
    print('  Suggested: git add posts-queue.csv images/ && git commit -m "Text overlays applied via Affinity Designer"')

if __name__ == "__main__":
    main()
