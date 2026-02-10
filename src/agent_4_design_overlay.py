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

def get_text_color_for_brightness(img, x, y, font, text):
    """
    Analyze image brightness at text location to choose black or white text.
    """
    try:
        # Sample area where text will be
        sample_width = 200
        sample_height = 100
        region = img.crop((
            max(0, x),
            max(0, y),
            min(img.width, x + sample_width),
            min(img.height, y + sample_height)
        ))

        # Calculate average brightness
        region_gray = region.convert('L')
        pixels = list(region_gray.getdata())
        avg_brightness = sum(pixels) / len(pixels)

        # Return black text for bright backgrounds, white for dark
        return (0, 0, 0) if avg_brightness > 127 else (255, 255, 255)
    except:
        return (0, 0, 0)  # Default to black

def apply_text_overlay(image_path, overlay_text, caption, output_path):
    """
    Apply large, bold text overlay for Instagram posts.

    Design approach (based on example):
    - Large, bold text directly on image (no background)
    - Text positioned prominently (left-center)
    - Very big font size for Instagram visibility
    - Black or white text based on image brightness
    - Caption and hashtags go in Instagram text box, NOT on image
    """
    try:
        # Open image
        img = Image.open(image_path)
        width, height = img.size

        # Convert to RGBA for drawing
        img = img.convert('RGBA')

        # Create transparent overlay
        txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # LARGE font size for Instagram - roughly 12-15% of image width
        base_font_size = int(width * 0.13)
        text_font = get_font(base_font_size)

        # Padding from edges
        padding = int(width * 0.08)  # 8% padding
        max_text_width = width - (padding * 2)

        # Wrap text to fit width
        lines = wrap_text(overlay_text, text_font, max_text_width, draw)

        # Calculate total text block height
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=text_font)
            line_heights.append(bbox[3] - bbox[1])

        total_text_height = sum(line_heights) + (len(lines) - 1) * int(base_font_size * 0.2)

        # Position text: left-center (like example)
        x_start = padding
        y_start = int(height * 0.3)  # Start at 30% down (upper-center area)

        # Determine text color based on background brightness
        text_color = get_text_color_for_brightness(img, x_start, y_start, text_font, overlay_text)

        # Calculate text bounding box for background
        # Add padding around text
        box_padding = int(base_font_size * 0.3)

        # Find max line width
        max_line_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=text_font)
            line_width = bbox[2] - bbox[0]
            max_line_width = max(max_line_width, line_width)

        # Draw semi-transparent background box for contrast
        # White box under black text, black box under white text
        box_color = (255, 255, 255) if text_color == (0, 0, 0) else (0, 0, 0)
        box_opacity = int(255 * 0.30)  # 30% opacity for better readability

        box_x1 = x_start - box_padding
        box_y1 = y_start - box_padding
        box_x2 = x_start + max_line_width + box_padding
        box_y2 = y_start + total_text_height + box_padding

        draw.rectangle(
            [box_x1, box_y1, box_x2, box_y2],
            fill=box_color + (box_opacity,)
        )

        # Draw each line
        y_offset = y_start
        for i, line in enumerate(lines):
            # Main text
            draw.text(
                (x_start, y_offset),
                line,
                font=text_font,
                fill=text_color + (255,)
            )

            y_offset += line_heights[i] + int(base_font_size * 0.2)

        # Composite text layer onto image
        img = Image.alpha_composite(img, txt_layer)

        # Convert to RGB and save
        final = img.convert('RGB')
        final.save(output_path, 'PNG', quality=95)

        return True

    except Exception as e:
        print(f"  ✗ Error applying overlay: {e}")
        import traceback
        traceback.print_exc()
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
            print(f"  Overlay text: {post['overlay_text']}")
            success = apply_text_overlay(
                image_path,
                post['overlay_text'],
                post['caption'],
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
