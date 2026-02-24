import asyncio
import uuid
from app.llm.litellm_client import execute_via_litellm
from app.db import SessionLocal
from sqlalchemy import select
from app.models import AgentCatalog

async def test_jessica_referral():
    print("--- Testing Jessica (GREETER-01) Elite Intelligence ---")
    
    with SessionLocal() as db:
        agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == 'Greeter-01')).scalars().first()
        if not agent:
            print("Jessica not found in DB!")
            return

        # Scenario 1: A technical bug inquiry (Should result in referral to SUPPORT-01)
        user_msg = "Hi, I'm trying to use your API but I keep getting a 500 error when I post to /v1/execute. Can you help me fix this?"
        print(f"\n[USER]: {user_msg}")
        
        result = await execute_via_litellm(
            provider=agent.llm_provider,
            model=agent.llm_model,
            system=agent.system_prompt,
            user=user_msg,
            org_id="org_test",
            agent_code=agent.code
        )
        
        response = result.get("response", "")
        print(f"\n[JESSICA]: {response}")
        
        if "[REFER:SUPPORT-01]" in response:
            print("\n✅ SUCCESS: Jessica correctly referred to Support.")
        else:
            print("\n❌ FAILURE: Jessica did not include the referral tag.")

if __name__ == "__main__":
    asyncio.run(test_jessica_referral())
