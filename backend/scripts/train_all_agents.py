from __future__ import annotations

import sys
from pathlib import Path
import argparse
import asyncio
import time

# Allow running as `python scripts/train_all_agents.py`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.academy.trainer import BatchTrainer


async def main() -> None:
    parser = argparse.ArgumentParser(description="Train all active agents with synthetic conversations.")
    parser.add_argument("--conversations", type=int, default=100, help="Conversations per agent (default: 100)")
    parser.add_argument("--batch-size", type=int, default=5, help="Agents per batch (default: 5)")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to wait between batches (default: 60)")
    args = parser.parse_args()

    trainer = BatchTrainer()

    print("\n" + "=" * 60)
    print("CREDDYPENS AGENT TRAINING")
    print("=" * 60)
    print(f"Conversations per agent: {args.conversations}")
    print(f"Batch size: {args.batch_size} agents at a time")
    print(f"Wait between batches: {args.wait}s")
    print("=" * 60 + "\n")

    start_time = time.time()
    await trainer.train_all_agents(
        conversations_per_agent=args.conversations,
        batch_size=args.batch_size,
        wait_s=args.wait,
    )
    elapsed = time.time() - start_time

    summary = await trainer.get_training_summary()

    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    print(f"Agents trained: {summary['total_agents']}")
    print(f"Average quality: {summary['avg_quality_overall']:.1f}/100")
    print(f"Total time: {elapsed/60:.1f} minutes")

    agents = summary.get("agents") or []
    print("\n" + "=" * 60)
    print("TOP 10 PERFORMERS")
    print("=" * 60)
    for i, a in enumerate(agents[:10], start=1):
        print(
            f"{i:2d}. {a['human_name'][:30]:30s} ({a['agent_code']:12s}) - {float(a.get('avg_quality_score') or 0):.1f}"
        )

    print("\n" + "=" * 60)
    print("BOTTOM 10 PERFORMERS")
    print("=" * 60)
    for i, a in enumerate(agents[-10:], start=1):
        print(
            f"{i:2d}. {a['human_name'][:30]:30s} ({a['agent_code']:12s}) - {float(a.get('avg_quality_score') or 0):.1f}"
        )

    print("\n" + "=" * 60)
    print("Training complete.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
