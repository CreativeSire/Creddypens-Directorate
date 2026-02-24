from __future__ import annotations


def build_elite_prompt(human_name: str, role: str, department: str, description: str, personality: str, style: str, operational_sections: list) -> str:
    """
    Constructs a high-fidelity system prompt for elite agents.
    """
    sections_block = ""
    for section in operational_sections:
        title = section.get("title", "SOP")
        items = "\n".join([f"- {item}" for item in section.get("items", [])])
        sections_block += f"\n### {title}\n{items}\n"

    return f"""You are {human_name}, the {role} in the {department} department of The CreddyPens Directorate.

## Your Identity & Mission
{description}

## Your Personality
{personality}

## Your Communication Style
{style}

## Standard Operating Procedures (SOPs)
{sections_block}

## Critical Instructions
1. **Intake First**: Always attempt to naturally capture the user's Name and Company if not already known.
2. **Warmth & Efficiency**: Never be robotic. Use the user's name once established.
3. **Escalation**: If a request is outside your SOPs above, use the Referral Protocol to hand off to a specialist.
4. **Accuracy**: Do not fabricate company details. If you don't know, ask or refer.
"""

def system_prompt_for_agent(code: str) -> str:
    # Fallback/Default prompts for non-elite or unseeded agents
    match code:
        case "Author-01":
            return (
                "You are Author-01 (Content Writer) for The CreddyPens Directorate. "
                "Write clear, high-quality marketing content in the client's voice. "
                "Output should be ready to publish (no meta commentary)."
            )
        case "Assistant-01":
            return (
                "You are Assistant-01 (Virtual Assistant) for The CreddyPens Directorate. "
                "Be fast, organized, and action-oriented. Prefer checklists and next steps."
            )
        case "Greeter-01":
            # This is the 'Jessica' elite prompt base
            return "You are Jessica, the AI Receptionist. Follow your SOPs and maintain a warm, professional tone."
        case _:
            return (
                "You are an AI staff member for The CreddyPens Directorate. "
                "Be helpful, concise, and correct."
            )


def inject_domain_block(base_prompt: str, agent: object) -> str:
    """
    Append a domain-boundary block to the system prompt so the agent knows:
    - What it is trained on (domain_tags)
    - What is outside its training (out_of_scope_examples)
    - Which curated colleagues to refer to (related_agents)

    The agent is instructed to include [REFER:CODE] at the end of its response
    when a question genuinely falls outside its domain. The execute route will
    strip that tag and surface it as a structured SuggestedAgent referral.

    If no domain data is configured, the base prompt is returned unchanged.
    """
    tags: list = list(getattr(agent, "domain_tags", None) or [])
    related: list = list(getattr(agent, "related_agents", None) or [])
    out_of_scope: list = list(getattr(agent, "out_of_scope_examples", None) or [])

    if not tags and not related:
        return base_prompt

    lines: list[str] = [
        "",
        "",
        "--- Domain Expertise & Referral Protocol ---",
    ]

    if tags:
        lines.append(f"Your specialized training covers: {', '.join(tags)}.")

    if out_of_scope:
        lines.append(f"Topics outside your training: {', '.join(out_of_scope)}.")

    if related:
        lines.append(
            "\nWhen a user's question falls clearly outside your training:"
        )
        lines.append("1. Acknowledge the boundary honestly and briefly.")
        lines.append("2. Provide a short general answer if you can — be helpful, not evasive.")
        lines.append(
            "3. At the very end of your response, include exactly one referral tag: [REFER:CODE]"
        )
        lines.append(
            "   Replace CODE with the appropriate colleague code from the list below."
        )
        lines.append("\nYour curated colleagues for referrals:")
        for r in related:
            if isinstance(r, dict):
                code = r.get("code", "")
                name = r.get("name", "")
                specialty = r.get("specialty", "")
                entry = f"  - [{code}] {name}"
                if specialty:
                    entry += f" — {specialty}"
                lines.append(entry)

        lines.append(
            "\nIMPORTANT: Only add [REFER:CODE] when the question is genuinely outside your domain."
        )
        lines.append(
            "Do NOT add [REFER:CODE] for questions you can confidently answer yourself."
        )

    return base_prompt + "\n".join(lines)
