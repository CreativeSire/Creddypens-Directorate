from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.routes import WorkflowExecuteIn, WorkflowStepIn, execute_agent, execute_workflow
from app.db import SessionLocal
from app.runtime.model_policy import model_policy_service
from app.schemas_execute import ExecuteContext, ExecuteIn


ORG_ID = "org_day21"


def _active_agents(db) -> list[str]:
    rows = db.execute(
        __import__("sqlalchemy").text(
            "select code from agent_catalog where status='active' order by code asc limit 5"
        )
    ).mappings().all()
    return [str(r["code"]) for r in rows]


def _ensure_hired(db, org_id: str, agent_code: str) -> None:
    text = __import__("sqlalchemy").text
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": "Day21 Test Org"},
    )
    row = db.execute(
        text(
            """
            select hired_agent_id
            from hired_agents
            where org_id=:org_id and agent_code=:agent_code and status='active'
            limit 1
            """
        ),
        {"org_id": org_id, "agent_code": agent_code},
    ).mappings().first()
    if row:
        db.commit()
        return
    db.execute(
        text(
            """
            insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
            values (gen_random_uuid(), :org_id, :agent_code, 'active', '{}'::jsonb)
            """
        ),
        {"org_id": org_id, "agent_code": agent_code},
    )
    db.commit()


def run() -> int:
    results: list[tuple[str, bool, str]] = []
    with SessionLocal() as db:
        agents = _active_agents(db)
        if len(agents) < 2:
            print("FAIL: need at least 2 active agents")
            return 1
        agent_a, agent_b = agents[0], agents[1]
        _ensure_hired(db, ORG_ID, agent_a)
        _ensure_hired(db, ORG_ID, agent_b)
        model_policy_service.upsert_preference(
            org_id=ORG_ID,
            preferred_provider="groq",
            preferred_model="llama-3.3-70b-versatile",
            reasoning_effort="medium",
            metadata={"source": "day21_integration_test"},
        )

        # 1) Web search integration
        out1 = execute_agent(
            agent_code=agent_a,
            payload=ExecuteIn(
                message="What's the current weather in New York?",
                session_id="day21-search",
                context=ExecuteContext(web_search=True, doc_retrieval=False),
            ),
            db=db,
            x_org_id=ORG_ID,
        )
        ok1 = bool(out1.search_used) and not bool(out1.docs_used)
        results.append(("web_search_only", ok1, f"search_used={out1.search_used}, docs_used={out1.docs_used}"))

        # 2) Document retrieval integration
        out2 = execute_agent(
            agent_code=agent_a,
            payload=ExecuteIn(
                message="What is your pricing structure?",
                session_id="day21-docs",
                context=ExecuteContext(web_search=False, doc_retrieval=True),
            ),
            db=db,
            x_org_id=ORG_ID,
        )
        ok2 = bool(out2.docs_used)
        results.append(("document_retrieval_only", ok2, f"search_used={out2.search_used}, docs_used={out2.docs_used}"))

        # 3) Session memory continuity
        session_id = "day21-memory"
        _ = execute_agent(
            agent_code=agent_a,
            payload=ExecuteIn(
                message="Remember that our preferred tone is concise and formal.",
                session_id=session_id,
                context=ExecuteContext(web_search=False, doc_retrieval=False),
            ),
            db=db,
            x_org_id=ORG_ID,
        )
        out3 = execute_agent(
            agent_code=agent_a,
            payload=ExecuteIn(
                message="What tone did I ask for earlier in this session?",
                session_id=session_id,
                context=ExecuteContext(web_search=False, doc_retrieval=False),
            ),
            db=db,
            x_org_id=ORG_ID,
        )
        content3 = (out3.response or "").lower()
        ok3 = ("concise" in content3) or ("formal" in content3)
        results.append(("session_memory", ok3, f"response_preview={out3.response[:120]!r}"))

        # 4) Workflow chaining
        wf = execute_workflow(
            payload=WorkflowExecuteIn(
                initial_message="Create a short customer welcome message, then polish it for professionalism.",
                session_id="day21-workflow",
                context=ExecuteContext(web_search=False, doc_retrieval=True, output_format="text"),
                steps=[
                    WorkflowStepIn(agent_code=agent_a, message="Draft version", use_previous_response=True),
                    WorkflowStepIn(agent_code=agent_b, message="Polish tone and clarity", use_previous_response=True),
                ],
            ),
            db=db,
            x_org_id=ORG_ID,
        )
        ok4 = len(wf.steps) == 2 and bool(wf.final_response.strip())
        results.append(("workflow_chaining", ok4, f"steps={len(wf.steps)}, final_len={len(wf.final_response or '')}"))

    print("\nDAY 21 INTEGRATION MATRIX")
    print("=" * 60)
    passed = 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:24s}  {detail}")
        if ok:
            passed += 1
    print("-" * 60)
    print(f"TOTAL: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
