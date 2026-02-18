from __future__ import annotations

import sys
from pathlib import Path
import argparse
import asyncio

# Allow running as `python scripts/test_single_training.py`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.academy.synthetic import SyntheticTrainer


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small synthetic training test for one agent.")
    parser.add_argument("--agent", default="Greeter-01", help="Agent code (default: Greeter-01)")
    parser.add_argument("--conversations", type=int, default=10, help="Conversations to run (default: 10)")
    args = parser.parse_args()

    trainer = SyntheticTrainer()
    print(f"Testing training with {args.agent} ({args.conversations} conversations)...\n")
    result = await trainer.train_agent(agent_code=args.agent, conversation_count=args.conversations)

    print("\nResult:")
    print(f"Agent: {result.get('human_name')} ({result.get('agent_code')})")
    print(f"Conversations: {result.get('conversations')}")
    print(f"Average Quality: {result.get('avg_quality_score')}/100")
    print(f"High scores (>=85): {result.get('high_scores')}")
    print(f"Low scores (<60): {result.get('low_scores')}")


if __name__ == "__main__":
    asyncio.run(main())
