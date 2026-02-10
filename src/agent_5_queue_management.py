"""
Agent 5: Queue Management and Status Tracking
Verifies pipeline completion and creates status report.
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import (
    CSV_PATH, CSV_COLUMNS, STATUS_PATH,
    STATUS_GENERATED, STATUS_APPROVED, STATUS_COMPLETE, STATUS_READY
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

def check_post_ready(post):
    """Check if a post is ready for Facebook."""
    return (
        post['image_status'] == STATUS_GENERATED
        and post['vision_status'] == STATUS_APPROVED
        and post['design_status'] == STATUS_COMPLETE
    )

def generate_status_report(posts):
    """Generate comprehensive status report."""
    total = len(posts)

    # Count statuses
    stats = {
        'image_generated': sum(1 for p in posts if p['image_status'] == STATUS_GENERATED),
        'vision_approved': sum(1 for p in posts if p['vision_status'] == STATUS_APPROVED),
        'design_complete': sum(1 for p in posts if p['design_status'] == STATUS_COMPLETE),
        'ready_for_facebook': sum(1 for p in posts if check_post_ready(p))
    }

    # Find blockers
    blockers = []
    for post in posts:
        if post['image_status'] == 'failed':
            blockers.append(f"{post['post_id']}: Image generation failed")
        elif post['vision_status'] == 'rejected':
            blockers.append(f"{post['post_id']}: Vision audit rejected")

    report = {
        'timestamp': datetime.now().isoformat(),
        'total_posts': total,
        'statistics': stats,
        'completion_rate': f"{stats['ready_for_facebook']}/{total}",
        'blockers': blockers,
        'ready_for_posting': stats['ready_for_facebook'] == total
    }

    return report

def main():
    """Main execution."""
    print("Agent 5: Queue Management and Status Tracking")
    print("=" * 50)

    # Read CSV
    posts = read_posts_csv()
    print(f"Found {len(posts)} posts in queue")

    # Generate status report
    report = generate_status_report(posts)

    # Display report
    print("\nPipeline Status:")
    print(f"  Total posts: {report['total_posts']}")
    print(f"  Images generated: {report['statistics']['image_generated']}")
    print(f"  Vision approved: {report['statistics']['vision_approved']}")
    print(f"  Designs complete: {report['statistics']['design_complete']}")
    print(f"  Ready for Facebook: {report['statistics']['ready_for_facebook']}")

    if report['blockers']:
        print("\nBlockers:")
        for blocker in report['blockers']:
            print(f"  ✗ {blocker}")
    else:
        print("\n✓ No blockers detected")

    # Update facebook_status for ready posts
    updated = False
    for post in posts:
        if check_post_ready(post) and post['facebook_status'] != STATUS_READY:
            post['facebook_status'] = STATUS_READY
            updated = True

    if updated:
        write_posts_csv(posts)
        print("\n✓ Updated CSV: marked ready posts for Facebook")

    # Save status report
    with open(STATUS_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Status report saved to {STATUS_PATH}")

    if report['ready_for_posting']:
        print("\n✓✓ All posts verified and ready for Task 6 (Facebook posting)")
        print('   Suggested: git add posts-queue.csv pipeline-status.json && git commit -m "Queue verified and ready for posting"')
    else:
        ready = report['statistics']['ready_for_facebook']
        total = report['total_posts']
        print(f"\n⚠ Pipeline incomplete: {ready}/{total} posts ready")
        print("  Resolve blockers before proceeding to Task 6")

if __name__ == "__main__":
    main()
