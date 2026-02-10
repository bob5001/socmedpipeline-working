"""
Agent 1: Campaign Data Generation
Reads campaign brief and generates posts queue CSV with post metadata.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, CAMPAIGN_ID, CAMPAIGN_BRIEF_PATH,
    STATUS_PENDING, OLLAMA_TEXT_MODEL, OLLAMA_BASE_URL
)

def generate_post_id():
    """Generate unique timestamped post ID."""
    return f"SS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def generate_posts_from_brief(num_posts=5):
    """
    Generate posts based on the campaign brief.
    Uses Ollama llama3.1 to create content aligned with campaign principles.
    """
    import ollama

    # Read the campaign brief
    with open(CAMPAIGN_BRIEF_PATH, 'r') as f:
        campaign_brief = f.read()

    prompt = f"""Based on this campaign brief, generate {num_posts} social media posts as JSON.

{campaign_brief}

Each post should:
- Follow one of the three content pillars: pattern_recognition, normalization, or gentle_orientation
- Use calm, observational, non-alarmist tone
- Include a detailed image_prompt describing a minimalist, calming scene (no text, no people's faces, architectural/environmental focus)
- Include caption text (40-80 words)
- Include 3-5 relevant hashtags

Return a JSON array with this structure:
[
  {{
    "content_pillar": "pattern_recognition",
    "image_prompt": "Minimal Scandinavian bedroom at dawn, soft natural light through sheer curtains, empty unmade bed, warm wood floors, single potted plant on windowsill, peaceful and still",
    "caption": "Have you noticed patterns in how you feel across different spaces? Some people report subtle shifts in comfort, sleep quality, or mental clarity depending on their environment. There's no right or wrong answer—just your own experience.",
    "hashtags": "#awareness #patterns #wellness #mindfulness #environment"
  }}
]

Generate {num_posts} diverse posts now:"""

    # Call Ollama
    response = ollama.chat(
        model=OLLAMA_TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    content = response['message']['content']

    # Extract JSON from response (may be wrapped in markdown)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    posts = json.loads(content)

    # Create CSV rows
    rows = []
    for post in posts:
        row = {
            "post_id": generate_post_id(),
            "campaign_id": CAMPAIGN_ID,
            "content_pillar": post["content_pillar"],
            "image_prompt": post["image_prompt"],
            "caption": post["caption"],
            "hashtags": post["hashtags"],
            "image_status": STATUS_PENDING,
            "vision_status": STATUS_PENDING,
            "design_status": STATUS_PENDING,
            "facebook_status": STATUS_PENDING
        }
        rows.append(row)

    return rows

def write_posts_csv(posts):
    """Write posts to CSV file."""
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(posts)

    print(f"✓ Created {len(posts)} posts in {CSV_PATH}")

def main():
    """Main execution."""
    print("Agent 1: Campaign Data Generation")
    print("=" * 50)

    # Generate posts
    print(f"Reading campaign brief from {CAMPAIGN_BRIEF_PATH}")
    print(f"Generating posts using {OLLAMA_TEXT_MODEL}...")

    posts = generate_posts_from_brief(num_posts=5)

    # Write to CSV
    write_posts_csv(posts)

    # Display summary
    print("\nGenerated Posts:")
    for post in posts:
        print(f"  - {post['post_id']}: {post['content_pillar']}")

    print("\n✓ Task 1 complete. Ready for git commit.")
    print('  Suggested: git add posts-queue.csv && git commit -m "Generated campaign posts from brief"')

if __name__ == "__main__":
    main()
