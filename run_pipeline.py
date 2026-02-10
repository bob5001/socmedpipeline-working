#!/usr/bin/env python3
"""
Main orchestrator for the social media campaign pipeline.
Runs all six agents in sequence with dependency checking.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src import (
    agent_1_campaign_data,
    agent_2_image_generation,
    agent_3_vision_audit,
    agent_4_design_overlay,
    agent_5_queue_management,
    agent_6_facebook_integration
)

def print_header(title):
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def run_agent(agent_module, agent_name):
    """Run a single agent and handle errors."""
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
    """Run the complete pipeline."""
    print("""
╔══════════════════════════════════════════════════════════╗
║   Social Media Campaign Pipeline                        ║
║   Multi-Agent Workflow for Content Generation           ║
╚══════════════════════════════════════════════════════════╝
    """)

    agents = [
        (agent_1_campaign_data, "Task 1: Campaign Data Generation"),
        (agent_2_image_generation, "Task 2: Image Generation via Replicate API"),
        (agent_3_vision_audit, "Task 3: Vision Audit and Approval"),
        (agent_4_design_overlay, "Task 4: Affinity Designer Text Overlay"),
        (agent_5_queue_management, "Task 5: Queue Management and Status Tracking"),
        (agent_6_facebook_integration, "Task 6: Facebook Business Manager Integration"),
    ]

    for i, (agent_module, agent_name) in enumerate(agents, 1):
        success = run_agent(agent_module, agent_name)

        if not success:
            print(f"\n✗ Pipeline stopped at Task {i}")
            print("  Fix errors above and re-run")
            sys.exit(1)

        # Prompt for continuation after each task
        if i < len(agents):
            response = input(f"\n→ Task {i} complete. Continue to Task {i+1}? [Y/n] ")
            if response.lower() == 'n':
                print(f"\n⏸  Pipeline paused after Task {i}")
                sys.exit(0)

    print_header("PIPELINE COMPLETE")
    print("✓✓ All six tasks completed successfully")
    print("   Draft posts ready for human review in Facebook Business Manager")
    print()

if __name__ == "__main__":
    main()
