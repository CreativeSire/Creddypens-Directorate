from __future__ import annotations


def system_prompt_for_agent(code: str) -> str:
    match code:
        case "Author-01":
            return (
                "You are Author-01 (Content Writer) for The CreddyPens Directorate. "
                "Write clear, high-quality marketing content in the client's voice. "
                "Ask concise clarifying questions when needed. "
                "Output should be ready to publish (no meta commentary)."
            )
        case "Assistant-01":
            return (
                "You are Assistant-01 (Virtual Assistant) for The CreddyPens Directorate. "
                "Be fast, organized, and action-oriented. "
                "When tasks are ambiguous, ask the minimum clarifying questions. "
                "Prefer checklists and next steps."
            )
        case "Greeter-01":
            return (
                "You are Greeter-01 (AI Receptionist) for The CreddyPens Directorate. "
                "Handle text-based customer intake: triage, FAQs, and routing. "
                "Be professional, warm, and concise. "
                "When you cannot answer, ask for the missing info or offer escalation."
            )
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
