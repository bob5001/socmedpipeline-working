"""
Agent 4: Text Overlay with Pillow
Opens approved images and overlays caption and hashtags using Python Pillow (PIL).
"""

import csv
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

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

def get_font(size):
    """
    Get a font for text rendering.
    Tries to use system fonts, falls back to PIL default.
    """
    font_options = [
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/System/Library/Fonts/SFNSDisplay.ttf",  # macOS San Francisco
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/Windows/Fonts/Arial.ttf",  # Windows
    ]

    for font_path in font_options:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue

    # Fallback to default
    try:
        return ImageFont.truetype("Arial.ttf", size)
    except:
        return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines

def apply_text_overlay(image_path, caption, hashtags, output_path):
    """
    Apply text overlay using Pillow.

    Design approach:
    - Clean, minimal aesthetic
    - Text positioned in bottom third with padding
    - Caption in larger font
    - Hashtags in smaller, lighter font
    - Semi-transparent dark overlay behind text for readability
    """
    try:
        # Open image
        img = Image.open(image_path)
        width, height = img.size

        # Create drawing context
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Font sizes
        caption_font = get_font(int(width * 0.025))  # ~2.5% of image width
        hashtag_font = get_font(int(width * 0.018))  # ~1.8% of image width

        # Text area dimensions
        padding = int(width * 0.05)  # 5% padding
        text_width = width - (padding * 2)
        text_start_y = int(height * 0.65)  # Start at 65% down

        # Add semi-transparent background for text area
        overlay_height = height - text_start_y + padding
        overlay_bg = Image.new('RGBA', (width, overlay_height), (0, 0, 0, 140))
        overlay.paste(overlay_bg, (0, text_start_y - padding))

        # Wrap and measure caption
        caption_lines = wrap_text(caption, caption_font, text_width, draw)

        # Draw caption
        y_offset = text_start_y
        for line in caption_lines:
            draw.text(
                (padding, y_offset),
                line,
                font=caption_font,
                fill=(255, 255, 255, 255)
            )
            bbox = draw.textbbox((0, 0), line, font=caption_font)
            line_height = bbox[3] - bbox[1]
            y_offset += line_height + 5

        # Add spacing
        y_offset += 15

        # Draw hashtags
        draw.text(
            (padding, y_offset),
            hashtags,
            font=hashtag_font,
            fill=(200, 200, 200, 255)
        )

        # Composite overlay onto original image
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)

        # Convert back to RGB for saving as PNG/JPEG
        final = img.convert('RGB')
        final.save(output_path, 'PNG', quality=95)

        return True

    except Exception as e:
        print(f"  ✗ Error applying overlay: {e}")
        return False

def main():
    """Main execution."""
    print("Agent 4: Text Overlay with Pillow")
    print("=" * 50)

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
    print('  Suggested: git add posts-queue.csv images/ && git commit -m "Text overlays applied with Pillow"')

if __name__ == "__main__":
    main()
