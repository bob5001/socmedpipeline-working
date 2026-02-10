"""
Agent 3: Vision Audit and Approval
Uses Ollama llava:7b to examine generated images and verify they match
the campaign tone and image prompt.
"""

import csv
import sys
from pathlib import Path
import ollama
import base64

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, IMAGES_DIR, CAMPAIGN_BRIEF_PATH,
    OLLAMA_VISION_MODEL,
    STATUS_GENERATED, STATUS_APPROVED, STATUS_REJECTED, STATUS_PENDING
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

def load_campaign_tone():
    """Extract key tone guidelines from campaign brief."""
    with open(CAMPAIGN_BRIEF_PATH, 'r') as f:
        brief = f.read()

    # Extract tone section
    tone_keywords = [
        "calm", "observational", "non-alarmist", "non-medical",
        "credible", "minimalist", "peaceful", "subtle"
    ]
    return tone_keywords

def audit_image(image_path, image_prompt, content_pillar):
    """
    Use Ollama vision model to audit image.
    Returns (approved: bool, reasoning: str)
    """
    try:
        # Read image as base64
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        tone_keywords = load_campaign_tone()

        prompt = f"""You are auditing a social media image for a wellness campaign about environmental awareness.

**Campaign Tone Requirements:**
- Calm, observational, non-alarmist
- Minimalist, peaceful aesthetics
- No people's faces visible
- No text overlays yet (will be added later)
- Architectural or environmental focus
- Subtle, credible, human

**Content Pillar:** {content_pillar}

**Expected Image:**
{image_prompt}

**Your Task:**
Examine this image and determine if it:
1. Matches the prompt description
2. Fits the campaign's calm, minimalist tone
3. Avoids alarmist or dramatic elements
4. Would work well for this wellness campaign

Respond in this format:
APPROVED or REJECTED
Reasoning: [1-2 sentences explaining your decision]"""

        # Call Ollama vision model
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [image_data]
            }]
        )

        result = response['message']['content']

        # Parse response
        approved = "APPROVED" in result.split('\n')[0].upper()
        reasoning = result.split("Reasoning:")[-1].strip() if "Reasoning:" in result else result

        return approved, reasoning

    except Exception as e:
        print(f"  ✗ Error during vision audit: {e}")
        return False, f"Error: {str(e)}"

def main():
    """Main execution."""
    print("Agent 3: Vision Audit and Approval")
    print("=" * 50)

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Filter posts needing vision audit
    pending_audits = [
        p for p in posts
        if p['image_status'] == STATUS_GENERATED
        and p['vision_status'] == STATUS_PENDING
    ]
    print(f"Posts needing vision audit: {len(pending_audits)}")

    if not pending_audits:
        print("No images ready for audit. Nothing to do.")
        return

    # Audit images
    updated = False
    for post in posts:
        if (post['image_status'] == STATUS_GENERATED
            and post['vision_status'] == STATUS_PENDING):

            image_path = IMAGES_DIR / f"{post['post_id']}.png"

            if not image_path.exists():
                print(f"✗ {post['post_id']}: Image file not found")
                post['vision_status'] = STATUS_REJECTED
                continue

            print(f"\n{post['post_id']} ({post['content_pillar']})")
            approved, reasoning = audit_image(
                image_path,
                post['image_prompt'],
                post['content_pillar']
            )

            if approved:
                post['vision_status'] = STATUS_APPROVED
                print(f"  ✓ APPROVED: {reasoning}")
            else:
                post['vision_status'] = STATUS_REJECTED
                print(f"  ✗ REJECTED: {reasoning}")

            updated = True

    # Save updated CSV
    if updated:
        write_posts_csv(posts)
        print(f"\n✓ Updated CSV with vision audit results")

    # Summary
    approved_count = sum(1 for p in posts if p['vision_status'] == STATUS_APPROVED)
    rejected_count = sum(1 for p in posts if p['vision_status'] == STATUS_REJECTED)

    print(f"\n✓ Task 3 complete.")
    print(f"  Approved: {approved_count}")
    print(f"  Rejected: {rejected_count}")
    print('  Suggested: git add posts-queue.csv && git commit -m "Vision audit completed"')

if __name__ == "__main__":
    main()
