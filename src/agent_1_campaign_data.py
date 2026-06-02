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
    STATUS_PENDING, ANTHROPIC_API_KEY, CLAUDE_MODEL
)

def generate_post_id():
    """Generate unique timestamped post ID with microseconds."""
    import time
    time.sleep(0.01)  # Small delay to ensure uniqueness
    return f"SS-{datetime.now().strftime('%Y%m%d-%H%M%S%f')[:20]}"

def load_campaign_brief(brief_path=None):
    """
    Load and normalize a campaign brief from either a JSON file (frontend output)
    or a legacy Markdown file. Returns a string ready to embed in an LLM prompt.
    """
    path = Path(brief_path) if brief_path else CAMPAIGN_BRIEF_PATH

    if path.suffix == '.json':
        with open(path, 'r') as f:
            data = json.load(f)
        lines = [
            f"# {data.get('business_name', 'Campaign')} — Social Media Campaign Brief",
            "",
            f"**Business:** {data.get('business_name', '')}",
            f"**Industry:** {data.get('industry', '')}",
            f"**Location:** {data.get('location', '')} / {data.get('service_area', '')}",
            f"**Target Audience:** {data.get('target_audience', '')}",
            f"**Customer Pain Point:** {data.get('customer_pain_point', '')}",
            f"**How Customers Find Them:** {data.get('discovery_channels', '')}",
            f"**Differentiator:** {data.get('differentiator', '')}",
            f"**Brand Voice:** {data.get('brand_voice', '')}",
            f"**Tone Notes:** {data.get('tone_notes', '')}",
            f"**Platforms:** {', '.join(data.get('platforms', []))}",
            f"**Posting Frequency:** {data.get('posting_frequency', '')}",
            f"**Content Sources:** {data.get('content_sources', '')}",
        ]
        if data.get('avoid_topics'):
            lines.append(f"**Avoid:** {', '.join(data['avoid_topics'])}")
        if data.get('emphasis_topics'):
            lines.append(f"**Emphasize:** {', '.join(data['emphasis_topics'])}")
        if data.get('upcoming_hooks'):
            lines.append("\n**Upcoming Hooks:**")
            for hook in data['upcoming_hooks']:
                lines.append(f"- {hook.get('event', '')} ({hook.get('date', '')}): {hook.get('notes', '')}")
        if data.get('raw_summary'):
            lines.append(f"\n**Summary:** {data['raw_summary']}")
        return "\n".join(lines)
    else:
        with open(path, 'r') as f:
            return f.read()


def generate_posts_from_brief(num_posts=5, focus="general", brief_path=None):
    """
    Generate posts based on the campaign brief.
    Uses Claude Haiku to create content aligned with campaign principles.

    Args:
        num_posts: Number of posts to generate
        focus: "general" (default) or "symptoms" (legacy EHS-specific path)
        brief_path: Optional path to a campaign brief file (.json or .md).
                    Defaults to CAMPAIGN_BRIEF_PATH from settings.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Read the campaign brief (JSON or markdown)
    campaign_brief = load_campaign_brief(brief_path)

    # Derive campaign_id and brief fields from JSON brief if available
    effective_campaign_id = CAMPAIGN_ID
    brief_data = {}
    resolved_path = Path(brief_path) if brief_path else CAMPAIGN_BRIEF_PATH
    if resolved_path.suffix == '.json':
        with open(resolved_path, 'r') as f:
            brief_data = json.load(f)
        biz = brief_data.get('business_name', '').lower().replace(' ', '-')
        if biz:
            effective_campaign_id = biz

    # EHS legacy path: inject symptom reference file
    extra_context = ""
    if focus == "symptoms":
        symptoms_file = Path(__file__).parent.parent / "common symptoms of ehs.md"
        if symptoms_file.exists():
            with open(symptoms_file, 'r') as f:
                extra_context = f"\n\nEHS SYMPTOMS TO REFERENCE:\n{f.read()}"

    # Derive content pillars from emphasis topics in brief, or use universal defaults
    emphasis = brief_data.get('emphasis_topics', [])
    if emphasis:
        pillar_guidance = (
            f"Choose content_pillar values that reflect this business's key themes. "
            f"Suggested pillars based on their brief: {', '.join(emphasis[:3])}. "
            f"You may also use: brand_awareness, social_proof, value_proposition, call_to_action."
        )
    else:
        pillar_guidance = (
            "Choose content_pillar values appropriate for this business. "
            "Good options: brand_awareness, social_proof, value_proposition, call_to_action, "
            "educational, community, promotional."
        )

    brand_voice = brief_data.get('brand_voice', 'professional')
    tone_notes = brief_data.get('tone_notes', '')
    tone_guidance = f"Brand voice: {brand_voice}. {tone_notes}".strip('. ')

    avoid = brief_data.get('avoid_topics', [])
    avoid_guidance = f"Avoid these topics: {', '.join(avoid)}." if avoid else ""

    prompt = f"""Based on this campaign brief, generate {num_posts} social media posts as a JSON array.

{campaign_brief}{extra_context}

Each post must:
- Have a content_pillar label that fits this specific business (not a generic template)
- {pillar_guidance}
- Tone: {tone_guidance}
- {avoid_guidance}
- Include a detailed image_prompt for a photo-realistic scene relevant to this business (no text in the image, no faces, focus on environment/work/product)
  IMPORTANT for image_prompt: Avoid bright backlighting or bright windows in the left-center area where text will be overlaid. Prefer evenly-lit or softly lit scenes.
- Include caption text (40-80 words) that speaks directly to this business's target audience and value proposition
- Include 3-5 relevant hashtags for this industry and location

Return a JSON array with this structure:
[
  {{
    "content_pillar": "social_proof",
    "image_prompt": "Modern commercial rooftop after a professional repair, clean seams and new membrane visible, Denver skyline in soft focus background, overcast sky, professional construction quality",
    "overlay_text": "Done right the first time.",
    "caption": "When a hail storm hit this Denver office complex, the property manager needed answers fast — not excuses. Our team was on-site within 24 hours, diagnosed the damage, and had the roof watertight before the next rain. That's what rapid response looks like.",
    "hashtags": "#Denver #CommercialConstruction #RoofRepair #PropertyManagement #SPCG"
  }}
]

IMPORTANT for overlay_text:
- Keep it SHORT (3-8 words maximum)
- Make it punchy and specific to this business — a headline, a proof point, a direct value statement
- This will be displayed in LARGE text on the image

Generate {num_posts} diverse posts that feel genuinely written for this specific business, not a generic template.

CRITICAL: Your entire response must be ONLY a valid JSON array. No introduction, no explanation, no markdown. Start with [ and end with ]. Each element must be a JSON object with exactly these keys: content_pillar, image_prompt, overlay_text, caption, hashtags."""

    # Call Claude
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    content = response.content[0].text

    # Extract JSON from response (may be wrapped in markdown or have intro text)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    else:
        # Look for JSON array start
        if '[' in content:
            start_idx = content.index('[')
            # Find matching closing bracket
            bracket_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(content)):
                if content[i] == '[':
                    bracket_count += 1
                elif content[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            content = content[start_idx:end_idx].strip()

    # Debug output
    if not content or content[0] not in '[{':
        print(f"\nRaw response from model:")
        print(content[:500])
        print("\n...parsing as best we can...")

    try:
        posts = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"\n✗ Failed to parse JSON from model response")
        print(f"  Error: {e}")
        print(f"\nFirst 200 chars of content:")
        print(content[:200])
        raise

    # Validate structure — the model sometimes returns a list of strings or a
    # wrapped object instead of the expected list of post dicts.
    if isinstance(posts, dict):
        # Unwrap {"posts": [...]} or {"data": [...]} if the model added a wrapper
        for key in ("posts", "data", "results", "items"):
            if key in posts and isinstance(posts[key], list):
                posts = posts[key]
                break

    REQUIRED_KEYS = {"content_pillar", "image_prompt", "overlay_text", "caption", "hashtags"}
    valid_posts = [p for p in posts if isinstance(p, dict) and REQUIRED_KEYS.issubset(p)]

    if not valid_posts:
        print(f"\n✗ Model returned {len(posts)} items but none had the required keys.")
        print(f"  Expected keys: {REQUIRED_KEYS}")
        print(f"  First item type: {type(posts[0]).__name__ if posts else 'empty list'}")
        print(f"  First item value: {str(posts[0])[:200] if posts else 'n/a'}")
        raise ValueError("Model output did not match expected post schema. Try re-running — the model may produce better output on the next attempt.")

    if len(valid_posts) < len(posts):
        print(f"  ⚠ Dropped {len(posts) - len(valid_posts)} malformed items from model output.")

    # Create CSV rows
    rows = []
    for post in valid_posts:
        row = {
            "post_id": generate_post_id(),
            "campaign_id": effective_campaign_id,
            "content_pillar": post["content_pillar"],
            "image_prompt": post["image_prompt"],
            "overlay_text": post["overlay_text"],
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
    import argparse
    parser = argparse.ArgumentParser(description="Agent 1: Campaign Data Generation")
    parser.add_argument("--brief", type=str, default=None,
                        help="Path to campaign brief (.json from frontend or .md legacy). "
                             "Defaults to CAMPAIGN_BRIEF_PATH in settings.")
    parser.add_argument("--focus", type=str, default="general",
                        choices=["symptoms", "general"],
                        help="Post generation focus (default: general). Use 'symptoms' for EHS/health-awareness campaigns only.")
    parser.add_argument("--num-posts", type=int, default=5,
                        help="Number of posts to generate (default: 5)")
    args = parser.parse_args()

    brief_path = args.brief or CAMPAIGN_BRIEF_PATH

    print("Agent 1: Campaign Data Generation")
    print("=" * 50)

    # Generate posts
    print(f"Reading campaign brief from {brief_path}")
    print(f"Generating posts using {CLAUDE_MODEL}...")

    posts = generate_posts_from_brief(num_posts=args.num_posts, focus=args.focus, brief_path=brief_path)

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
