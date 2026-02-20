from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import text

# Allow running as `python scripts/update_prompts.py`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.schema import ensure_schema
from data.prompt_improvements import PROMPT_IMPROVEMENTS


def _parse_agents(arg: str | None) -> list[str]:
    if not arg:
        return list(PROMPT_IMPROVEMENTS.keys())
    return [a.strip() for a in arg.split(",") if a.strip()]


def apply_prompt_updates(*, agents: list[str], apply: bool = False) -> None:
    missing = [a for a in agents if a not in PROMPT_IMPROVEMENTS]
    if missing:
        raise ValueError(f"No prompt patch found for: {', '.join(missing)}")

    with SessionLocal() as db:
        ensure_schema(db.get_bind())

        print(f"Target agents: {len(agents)}")
        for agent_code in agents:
            prompt = PROMPT_IMPROVEMENTS[agent_code]
            current = db.execute(
                text("select system_prompt from agent_catalog where code = :code"),
                {"code": agent_code},
            ).scalar_one_or_none()

            if current is None:
                print(f"[SKIP] {agent_code}: not found in agent_catalog")
                continue

            if not apply:
                print(f"[DRY-RUN] {agent_code}: patch ready ({len(prompt)} chars)")
                continue

            next_version = db.execute(
                text("select coalesce(max(version), 0) + 1 from system_prompt_versions where agent_code = :code"),
                {"code": agent_code},
            ).scalar_one()

            db.execute(
                text(
                    """
                    insert into system_prompt_versions
                      (agent_code, version, system_prompt, created_by, performance_notes, is_active)
                    values
                      (:agent_code, :version, :system_prompt, :created_by, :performance_notes, true)
                    """
                ),
                {
                    "agent_code": agent_code,
                    "version": int(next_version),
                    "system_prompt": prompt,
                    "created_by": "day16_manual_optimization",
                    "performance_notes": "Week3 Day16 patch: improve helpfulness/completeness and reduce role-refusal patterns",
                },
            )

            db.execute(
                text("update system_prompt_versions set is_active = false where agent_code = :code and version <> :version"),
                {"code": agent_code, "version": int(next_version)},
            )

            db.execute(
                text("update agent_catalog set system_prompt = :system_prompt, updated_at = now() where code = :code"),
                {"system_prompt": prompt, "code": agent_code},
            )

            print(f"[APPLIED] {agent_code}: version {int(next_version)}")

        if apply:
            db.commit()
            print("Prompt updates committed.")
        else:
            print("Dry-run complete. Re-run with --apply to persist changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply Day16 prompt improvements for selected agents.")
    parser.add_argument(
        "--agents",
        type=str,
        default="",
        help="Comma-separated agent codes. Default: all codes in PROMPT_IMPROVEMENTS.",
    )
    parser.add_argument("--apply", action="store_true", help="Persist updates to DB (default is dry-run).")
    parser.add_argument(
        "--export-json",
        type=str,
        default="",
        help="Optional path to export selected patch payload for review.",
    )
    args = parser.parse_args()

    selected = _parse_agents(args.agents)

    if args.export_json:
        out = Path(args.export_json)
        if not out.is_absolute():
            out = BACKEND_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({k: PROMPT_IMPROVEMENTS[k] for k in selected}, indent=2),
            encoding="utf-8",
        )
        print(f"Patch export written: {out}")

    apply_prompt_updates(agents=selected, apply=args.apply)

