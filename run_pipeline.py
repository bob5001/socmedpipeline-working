#!/usr/bin/env python3
"""
Main orchestrator for the social media campaign pipeline.
Runs all six agents in sequence with dependency checking.
"""

import sys
import os
import json
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def run_agent(agent_module, agent_name):
    print_header(agent_name)
    try:
        agent_module.main()
        return True
    except Exception as e:
        print(f"\n✗ Error in {agent_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Social Media Campaign Pipeline")
    parser.add_argument(
        "--brief",
        type=str,
        default=None,
        help="Path to a brief JSON file produced by the frontend. "
             "Creates an isolated output directory under campaigns/{brief_id}/.",
    )
    parser.add_argument(
        "--focus", type=str, default="general", choices=["general", "symptoms"],
        help="Post generation focus passed to Agent 1 (default: general).",
    )
    parser.add_argument(
        "--num-posts", type=int, default=5,
        help="Number of posts to generate (default: 5).",
    )
    args = parser.parse_args()

    # --- Resolve campaign output directory ---
    if args.brief:
        brief_path = Path(args.brief).resolve()
        if not brief_path.exists():
            print(f"✗ Brief file not found: {brief_path}")
            sys.exit(1)

        with open(brief_path) as f:
            brief_data = json.load(f)

        brief_id = brief_data.get("id", brief_path.stem)
        campaign_dir = Path(__file__).parent / "campaigns" / brief_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        # Set env vars BEFORE importing agents so settings.py picks them up
        os.environ["CAMPAIGN_DIR"] = str(campaign_dir)
        os.environ["CAMPAIGN_BRIEF_PATH"] = str(brief_path)

        print(f"  Brief:    {brief_path}")
        print(f"  Output:   {campaign_dir}")
    else:
        brief_id = "legacy"
        print("  No --brief supplied — using default paths from settings.")

    # Import agents AFTER env vars are set so config.settings evaluates correctly
    from src import (
        agent_1_campaign_data,
        agent_2_image_generation,
        agent_3_vision_audit,
        agent_4_design_overlay,
        agent_5_queue_management,
        agent_6_instagram_integration,
    )

    print("""
╔══════════════════════════════════════════════════════════╗
║   Social Media Campaign Pipeline                        ║
║   Multi-Agent Workflow for Content Generation           ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Patch sys.argv so Agent 1 picks up --focus and --num-posts without a
    # separate argparse pass-through. Other agents ignore unknown argv entries.
    agent1_argv = [sys.argv[0]]
    if args.brief:
        agent1_argv += ["--brief", str(brief_path)]
    agent1_argv += ["--focus", args.focus, "--num-posts", str(args.num_posts)]
    original_argv = sys.argv
    sys.argv = agent1_argv

    agents = [
        (agent_1_campaign_data,         "Task 1: Campaign Data Generation"),
        (agent_2_image_generation,      "Task 2: Image Generation via Replicate API"),
        (agent_3_vision_audit,          "Task 3: Vision Audit and Approval"),
        (agent_4_design_overlay,        "Task 4: Text Overlay with Pillow"),
        (agent_5_queue_management,      "Task 5: Queue Management and Status Tracking"),
        (agent_6_instagram_integration, "Task 6: Instagram Graph API Integration"),
    ]

    for i, (agent_module, agent_name) in enumerate(agents, 1):
        # Restore argv after Agent 1 so subsequent agents parse cleanly
        if i == 2:
            sys.argv = original_argv

        success = run_agent(agent_module, agent_name)

        if not success:
            print(f"\n✗ Pipeline stopped at Task {i}")
            print("  Fix errors above and re-run")
            sys.exit(1)

        if i < len(agents):
            response = input(f"\n→ Task {i} complete. Continue to Task {i+1}? [Y/n] ")
            if response.lower() == "n":
                print(f"\n⏸  Pipeline paused after Task {i}")
                sys.exit(0)

    print_header("PIPELINE COMPLETE")
    print("✓✓ All six tasks completed successfully")
    if args.brief:
        print(f"   Campaign outputs: campaigns/{brief_id}/")
    print()


if __name__ == "__main__":
    main()
