from __future__ import annotations

import sys
from pathlib import Path
import asyncio

from sqlalchemy import select, text

# Allow running as `python scripts/test_evaluator.py` or `python -m scripts.test_evaluator`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.academy.evaluator import ResponseEvaluator
from app.db import SessionLocal
from app.llm.litellm_client import execute_via_litellm
from app.models import AgentCatalog


async def test_single_evaluation() -> None:
    evaluator = ResponseEvaluator()

    user_message = "Hi, I need help with my account login. I forgot my password."
    agent_response = (
        "I can help you reset your password. Please use the 'Forgot password' link on the login page, "
        "then check your email for the reset link. If you don’t receive it within a few minutes, tell me "
        "the email domain you’re using and I’ll help you troubleshoot."
    )

    print("Testing Response Evaluator (hardcoded)...")
    print(f"\nUser: {user_message}")
    print(f"Agent: {agent_response}")

    evaluation = await evaluator.evaluate(
        user_message=user_message,
        agent_response=agent_response,
        agent_role="Technical Support Specialist",
        expected_qualities=["helpful", "clear", "professional"],
    )

    print("\nResults:")
    print(f"Overall Score: {evaluation['overall']}/100")
    for criterion, score in evaluation["subscores"].items():
        print(f"  {criterion}: {score}/100")


async def test_with_real_agent() -> None:
    evaluator = ResponseEvaluator()

    with SessionLocal() as db:
        scenario = (
            db.execute(
                text(
                    """
                    select agent_code, user_message, expected_qualities
                    from test_scenarios
                    where agent_code = :code
                    order by created_at desc
                    limit 1;
                    """
                ),
                {"code": "Greeter-01"},
            )
            .mappings()
            .first()
        )

        if not scenario:
            print("No scenarios found for Greeter-01")
            return

        agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == "Greeter-01")).scalars().first()
        if not agent:
            print("Agent Greeter-01 not found in agent_catalog")
            return

    print("\nTesting Response Evaluator (real agent response)...")
    print(f"\nScenario: {scenario['user_message']}")

    # Generate a real (or mocked) agent response.
    result = execute_via_litellm(
        provider=agent.llm_provider,
        model=agent.llm_model,
        system=(agent.system_prompt or "").strip() or f"You are {agent.name}.",
        user=scenario["user_message"],
    )
    agent_response = (result.get("response") or "").strip()

    print(f"\nAgent responded (first 200 chars): {agent_response[:200]!r}")

    evaluation = await evaluator.evaluate(
        user_message=scenario["user_message"],
        agent_response=agent_response,
        agent_role=agent.name or "AI Receptionist",
        expected_qualities=list(scenario.get("expected_qualities") or []),
    )

    print("\nResults:")
    print(f"Overall Score: {evaluation['overall']}/100")
    for criterion, score in evaluation["subscores"].items():
        print(f"  {criterion}: {score}/100")


async def main() -> None:
    print("=" * 60)
    print("RESPONSE EVALUATOR TEST")
    print("=" * 60)

    print("\n[TEST 1] Hardcoded conversation")
    await test_single_evaluation()

    print("\n\n[TEST 2] Real agent response")
    await test_with_real_agent()

    print("\n" + "=" * 60)
    print("Tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
