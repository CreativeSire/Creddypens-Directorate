from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    scenario_type: str
    difficulty: str
    user_message: str
    expected_qualities: list[str]


class ScenarioGenerator:
    """
    v1 scenario generator (Week 1 foundation).
    Generates synthetic user messages for training/evaluation, mapped by coarse agent role.
    """

    SCENARIOS: dict[str, list[dict]] = {
        "AI Receptionist": [
            {
                "type": "greeting",
                "difficulty": "easy",
                "template": "Hi there — are you open {time_of_day}? I'm looking for help with {topic}.",
                "times": ["today", "this weekend", "after hours", "right now"],
                "topics": ["booking", "pricing", "services", "support"],
                "qualities": ["warm greeting", "clarifying question if needed", "no fabrication"],
            },
            {
                "type": "appointment",
                "difficulty": "medium",
                "template": "Can you {action} an appointment for a {service} {timing}?",
                "actions": ["schedule", "reschedule", "cancel"],
                "services": ["consultation", "demo", "meeting", "service"],
                "timings": ["tomorrow", "next week", "this afternoon", "in two hours"],
                "qualities": ["collect name", "collect purpose", "route/escalate appropriately"],
            },
            {
                "type": "complaint",
                "difficulty": "hard",
                "template": "I'm upset about {issue}. I need {resolution} now.",
                "issues": ["a billing error", "a delayed response", "poor service", "a broken link"],
                "resolutions": ["a call back", "a refund", "an escalation", "a fix"],
                "qualities": ["de-escalation", "no pricing promises", "handoff to team"],
            },
        ],
        "Sales Development Representative": [
            {
                "type": "qualification",
                "difficulty": "medium",
                "template": "I'm a {title} at a {size} company. We're evaluating {solution}.",
                "title": ["CEO", "VP Sales", "Marketing Director", "Ops Manager"],
                "size": ["startup", "mid-market", "enterprise"],
                "solution": ["automation", "analytics", "customer support tooling", "sales enablement"],
                "qualities": ["ask qualifying questions", "summarize needs", "suggest next step"],
            },
            {
                "type": "objection",
                "difficulty": "hard",
                "template": "This seems {objection}. Why should we switch?",
                "objection": ["too expensive", "complicated", "risky", "not urgent"],
                "qualities": ["handle objection", "stay consultative", "avoid guarantees"],
            },
        ],
        "Technical Support Specialist": [
            {
                "type": "simple_troubleshooting",
                "difficulty": "easy",
                "template": "I can't {action}. I'm seeing '{error}'.",
                "action": ["log in", "export a report", "save changes", "invite a teammate"],
                "error": ["permission denied", "timeout", "server error", "unknown error"],
                "qualities": ["step-by-step", "ask environment", "safe troubleshooting"],
            },
            {
                "type": "frustrated_user",
                "difficulty": "hard",
                "template": "This is the {n} time this happened. I'm frustrated. Fix it.",
                "n": ["third", "fifth", "tenth"],
                "qualities": ["empathy", "calm tone", "collect repro steps"],
            },
        ],
        "Content Writer": [
            {
                "type": "content_request",
                "difficulty": "medium",
                "template": "Write a {format} about {topic} for a {industry} brand. Tone: {tone}.",
                "format": ["blog intro", "LinkedIn post", "email sequence outline", "YouTube hook"],
                "topic": ["AI automation", "customer retention", "brand positioning", "lead generation"],
                "industry": ["SaaS", "agency", "e-commerce", "healthcare"],
                "tone": ["authoritative", "friendly", "bold", "minimalist"],
                "qualities": ["structured output", "one clarifying question if missing info", "no copyright violations"],
            }
        ],
        "Virtual Assistant": [
            {
                "type": "ops_support",
                "difficulty": "medium",
                "template": "Help me organize {thing}. Provide a checklist and next actions.",
                "thing": ["my inbox", "my weekly priorities", "a meeting agenda", "a travel plan"],
                "qualities": ["concise checklist", "no external access", "confirm assumptions"],
            }
        ],
    }

    def infer_bucket(self, role: str) -> str:
        r = (role or "").lower()
        if "reception" in r or "greeter" in r:
            return "AI Receptionist"
        if "sales" in r or "sdr" in r or "closer" in r:
            return "Sales Development Representative"
        if "support" in r or "technical" in r or "it" in r:
            return "Technical Support Specialist"
        if "writer" in r or "content" in r or "author" in r:
            return "Content Writer"
        if "assistant" in r:
            return "Virtual Assistant"
        return "Virtual Assistant"

    def generate(self, *, role: str, count: int = 25) -> list[Scenario]:
        count = max(1, min(250, int(count)))
        bucket = self.infer_bucket(role)
        templates = self.SCENARIOS.get(bucket) or []
        if not templates:
            return []
        out: list[Scenario] = []
        for _ in range(count):
            t = random.choice(templates)
            msg = t["template"]
            for key, val in list(t.items()):
                if key in {"type", "difficulty", "template", "qualities"}:
                    continue
                choices = val
                if isinstance(choices, list) and choices:
                    msg = msg.replace("{" + key + "}", random.choice(choices))
            out.append(
                Scenario(
                    scenario_type=t["type"],
                    difficulty=t["difficulty"],
                    user_message=msg,
                    expected_qualities=list(t.get("qualities") or []),
                )
            )
        return out

