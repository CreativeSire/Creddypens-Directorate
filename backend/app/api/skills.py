from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Marketplace — browse
# ---------------------------------------------------------------------------

@router.get("/v1/skills")
def list_skills(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return all active skills in the marketplace, optionally filtered by category."""
    sql = """
        select
          skill_id, name, category, description, author,
          compatible_agents, domain_tags, tool_actions,
          price_cents, status, install_count, created_at
        from skill_catalog
        where status = 'active'
        {category_filter}
        order by category asc, price_cents asc, name asc;
    """
    if category:
        rows = db.execute(
            text(sql.format(category_filter="and category = :category")),
            {"category": category},
        ).mappings().all()
    else:
        rows = db.execute(text(sql.format(category_filter=""))).mappings().all()

    return [_skill_row(r) for r in rows]


@router.get("/v1/skills/{skill_id}")
def get_skill(skill_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.execute(
        text("select * from skill_catalog where skill_id = :sid"),
        {"sid": skill_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_row(row)


# ---------------------------------------------------------------------------
# Org — view installed skills
# ---------------------------------------------------------------------------

@router.get("/v1/organizations/{org_id}/skills")
def list_org_skills(org_id: str, db: Session = Depends(get_db)) -> list[dict]:
    """All skills installed for the org (org-wide + per-agent)."""
    rows = db.execute(
        text("""
            select
              si.installation_id, si.org_id, si.agent_code, si.installed_at,
              sc.skill_id, sc.name, sc.category, sc.description,
              sc.compatible_agents, sc.domain_tags, sc.price_cents, sc.status
            from skill_installations si
            join skill_catalog sc on sc.skill_id = si.skill_id
            where si.org_id = :org_id
            order by si.installed_at desc;
        """),
        {"org_id": org_id},
    ).mappings().all()
    return [_install_row(r) for r in rows]


@router.get("/v1/organizations/{org_id}/agents/{agent_code}/skills")
def list_agent_skills(
    org_id: str,
    agent_code: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Skills installed for a specific agent (agent-specific + org-wide)."""
    rows = db.execute(
        text("""
            select
              si.installation_id, si.org_id, si.agent_code, si.installed_at,
              sc.skill_id, sc.name, sc.category, sc.description,
              sc.compatible_agents, sc.domain_tags, sc.price_cents, sc.status
            from skill_installations si
            join skill_catalog sc on sc.skill_id = si.skill_id
            where si.org_id = :org_id
              and (si.agent_code = :agent_code or si.agent_code is null)
            order by si.installed_at desc;
        """),
        {"org_id": org_id, "agent_code": agent_code},
    ).mappings().all()
    return [_install_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Install / uninstall — agent-scoped
# ---------------------------------------------------------------------------

@router.post("/v1/organizations/{org_id}/agents/{agent_code}/skills/{skill_id}")
def install_skill_for_agent(
    org_id: str,
    agent_code: str,
    skill_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    """Install a skill pack for a specific agent."""
    eff_org = x_org_id or org_id

    skill = db.execute(
        text("select skill_id, name from skill_catalog where skill_id = :sid and status = 'active'"),
        {"sid": skill_id},
    ).mappings().first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found or inactive")

    try:
        db.execute(
            text("""
                insert into skill_installations (installation_id, org_id, agent_code, skill_id)
                values (:iid, :org_id, :agent_code, :skill_id)
                on conflict do nothing;
            """),
            {
                "iid": str(uuid.uuid4()),
                "org_id": eff_org,
                "agent_code": agent_code,
                "skill_id": skill_id,
            },
        )
        db.execute(
            text("update skill_catalog set install_count = install_count + 1 where skill_id = :sid"),
            {"sid": skill_id},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Install failed: {exc}") from exc

    return {"ok": True, "org_id": eff_org, "agent_code": agent_code, "skill_id": skill_id, "action": "installed"}


@router.delete("/v1/organizations/{org_id}/agents/{agent_code}/skills/{skill_id}")
def uninstall_skill_for_agent(
    org_id: str,
    agent_code: str,
    skill_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    eff_org = x_org_id or org_id
    db.execute(
        text("""
            delete from skill_installations
            where org_id = :org_id and agent_code = :agent_code and skill_id = :skill_id
        """),
        {"org_id": eff_org, "agent_code": agent_code, "skill_id": skill_id},
    )
    db.commit()
    return {"ok": True, "org_id": eff_org, "agent_code": agent_code, "skill_id": skill_id, "action": "uninstalled"}


# ---------------------------------------------------------------------------
# Install / uninstall — org-wide (no specific agent)
# ---------------------------------------------------------------------------

@router.post("/v1/organizations/{org_id}/skills/{skill_id}")
def install_skill_org_wide(
    org_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    """Install a skill org-wide — all agents in the org benefit."""
    eff_org = x_org_id or org_id

    skill = db.execute(
        text("select skill_id, name from skill_catalog where skill_id = :sid and status = 'active'"),
        {"sid": skill_id},
    ).mappings().first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found or inactive")

    try:
        db.execute(
            text("""
                insert into skill_installations (installation_id, org_id, agent_code, skill_id)
                values (:iid, :org_id, null, :skill_id)
                on conflict do nothing;
            """),
            {"iid": str(uuid.uuid4()), "org_id": eff_org, "skill_id": skill_id},
        )
        db.execute(
            text("update skill_catalog set install_count = install_count + 1 where skill_id = :sid"),
            {"sid": skill_id},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Install failed: {exc}") from exc

    return {"ok": True, "org_id": eff_org, "agent_code": None, "skill_id": skill_id, "action": "installed_org_wide"}


@router.delete("/v1/organizations/{org_id}/skills/{skill_id}")
def uninstall_skill_org_wide(
    org_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    eff_org = x_org_id or org_id
    db.execute(
        text("""
            delete from skill_installations
            where org_id = :org_id and agent_code is null and skill_id = :skill_id
        """),
        {"org_id": eff_org, "skill_id": skill_id},
    )
    db.commit()
    return {"ok": True, "org_id": eff_org, "skill_id": skill_id, "action": "uninstalled_org_wide"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skill_row(r: dict) -> dict:
    def _j(v: object) -> list:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return []

    created = r.get("created_at")
    return {
        "skill_id": r["skill_id"],
        "name": r["name"],
        "category": r["category"],
        "description": r["description"],
        "author": r.get("author", "Directorate"),
        "compatible_agents": _j(r.get("compatible_agents")),
        "domain_tags": _j(r.get("domain_tags")),
        "tool_actions": _j(r.get("tool_actions")),
        "price_cents": int(r.get("price_cents") or 0),
        "status": r.get("status", "active"),
        "install_count": int(r.get("install_count") or 0),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }


def _install_row(r: dict) -> dict:
    def _j(v: object) -> list:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return []

    installed = r.get("installed_at")
    return {
        "installation_id": str(r["installation_id"]),
        "org_id": r["org_id"],
        "agent_code": r.get("agent_code"),
        "installed_at": installed.isoformat() if hasattr(installed, "isoformat") else installed,
        "skill": {
            "skill_id": r["skill_id"],
            "name": r["name"],
            "category": r["category"],
            "description": r["description"],
            "compatible_agents": _j(r.get("compatible_agents")),
            "domain_tags": _j(r.get("domain_tags")),
            "price_cents": int(r.get("price_cents") or 0),
            "status": r.get("status", "active"),
        },
    }
