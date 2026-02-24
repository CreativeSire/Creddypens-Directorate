from __future__ import annotations

"""
Seed the skill_catalog table with the initial CreddyPens skill marketplace.
Run once (or re-run safely — uses ON CONFLICT DO UPDATE).

    python scripts/seed_skills.py
"""

import json
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import engine
from app.schema import ensure_schema


SKILLS: list[dict] = [
    # ── Marketing & Creative ──────────────────────────────────────────────────
    {
        "skill_id": "marketing-pro",
        "name": "Marketing Pro Frameworks",
        "category": "Marketing & Creative",
        "description": (
            "Arm your marketing agents with proven copywriting and campaign frameworks — "
            "AIDA, PAS, StoryBrand, and the Fogg Behavior Model. "
            "Agents gain structured templates for ads, landing pages, and launch sequences."
        ),
        "author": "Directorate",
        "compatible_agents": ["Author-01", "SOCIAL-01", "EMAIL-01", "BRAND-01", "VIDEO-01"],
        "prompt_injection": (
            "You have the Marketing Pro skill pack installed.\n"
            "Available frameworks: AIDA (Attention → Interest → Desire → Action), "
            "PAS (Problem → Agitate → Solution), StoryBrand (Hero/Problem/Guide/Plan/CTA), "
            "Fogg Behavior Model (Motivation + Ability + Trigger).\n"
            "When producing marketing content, proactively select and apply the best-fit framework. "
            "Label the framework used at the top of your output."
        ),
        "domain_tags": ["AIDA", "PAS", "StoryBrand", "copywriting frameworks", "launch sequences"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "content-repurpose",
        "name": "Content Repurposing Engine",
        "category": "Marketing & Creative",
        "description": (
            "Turn any piece of content into 10+ formats instantly. "
            "Blog post → Twitter thread, LinkedIn carousel, email newsletter, YouTube script, "
            "Instagram caption, and short-form video script."
        ),
        "author": "Directorate",
        "compatible_agents": ["Author-01", "SOCIAL-01", "VIDEO-01", "EMAIL-01"],
        "prompt_injection": (
            "You have the Content Repurposing Engine skill installed.\n"
            "When asked to repurpose content, automatically produce all relevant format variants: "
            "Twitter/X thread (10 tweets), LinkedIn post, Instagram caption, YouTube script outline, "
            "email newsletter section, and short-form video script (60s).\n"
            "Label each variant clearly with its platform name and character/word count."
        ),
        "domain_tags": ["content repurposing", "multi-format", "cross-channel", "social adaptation"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "seo-advanced",
        "name": "Advanced SEO Toolkit",
        "category": "Marketing & Creative",
        "description": (
            "Technical SEO mastery built in. Schema markup generation, "
            "Core Web Vitals guidance, E-E-A-T principles, and structured "
            "on-page SEO checklists baked into every content output."
        ),
        "author": "Directorate",
        "compatible_agents": ["SEO-01", "Author-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the Advanced SEO Toolkit skill installed.\n"
            "For every content or analysis task, automatically apply: "
            "E-E-A-T principles (Experience, Expertise, Authoritativeness, Trustworthiness), "
            "structured on-page SEO checklist (title tag, meta description, H1-H6 hierarchy, "
            "internal linking, schema markup type), Core Web Vitals impact notes.\n"
            "End every SEO audit with a prioritised action list scored by impact vs effort.\n"
            "GENERATIVE ENGINE OPTIMIZATION (GEO) — 2025 addition:\n"
            "GEO complements SEO by optimising for AI-powered search engines (Google AI Overviews, "
            "ChatGPT Search, Perplexity). 58% of users use AI tools for product discovery in 2025.\n"
            "GEO principles to apply alongside standard SEO:\n"
            "Write structured, quotable paragraphs that can stand alone as complete answers. "
            "AI engines excerpt specific passages — avoid burying answers in long prose.\n"
            "Build authority signals: citations, expert bylines, original data/research, "
            "and earned media coverage (AI search has earned media bias toward cited sources).\n"
            "Semantic entity coverage: build topical authority clusters covering the full topic graph. "
            "Use Wikipedia/Wikidata-aligned entity naming for knowledge graph inclusion.\n"
            "Platform-specific: for Google AI Overviews — use FAQ schema, target Position 0; "
            "for ChatGPT Search (Bing-powered) — ensure Bingbot access, submit Bing Webmaster sitemap; "
            "for Perplexity — use clear publication dates, fresh content, cite primary sources.\n"
            "E-E-A-T 2025: Experience (first-hand) now equals Expertise in weighting. "
            "Demonstrate with original data, case studies, real examples, product testing."
        ),
        "domain_tags": ["technical SEO", "schema markup", "Core Web Vitals", "E-E-A-T", "on-page SEO", "GEO", "AI search"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "email-sequences-pro",
        "name": "Email Sequence Library",
        "category": "Marketing & Creative",
        "description": (
            "Pre-built email sequence templates: cold outreach (5-touch), "
            "sales nurture (7-email), re-engagement, win-back, and post-purchase. "
            "Includes subject line formulas and A/B test variants."
        ),
        "author": "Directorate",
        "compatible_agents": ["EMAIL-01", "HUNTER-01", "Author-01"],
        "prompt_injection": (
            "You have the Email Sequence Library skill installed.\n"
            "Available sequence templates: cold outreach (5-touch: pattern interrupt → value → social proof → objection → break-up), "
            "sales nurture (7-email: welcome → pain → solution → proof → FAQ → urgency → CTA), "
            "re-engagement (3-email: we miss you → value reminder → last chance), "
            "win-back (4-email: check-in → exclusive offer → FOMO → goodbye).\n"
            "For each email, provide: subject line (A + B variant), preview text, body, and CTA.\n"
            "Label open rate expectations per sequence step based on industry benchmarks."
        ),
        "domain_tags": ["email sequences", "cold outreach", "nurture flows", "A/B testing", "subject lines"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    # ── Sales & Business Dev ──────────────────────────────────────────────────
    {
        "skill_id": "sales-closer-pro",
        "name": "Sales Closing Mastery",
        "category": "Sales & Business Dev",
        "description": (
            "SPIN Selling, Challenger Sale, and Sandler methodology built in. "
            "Objection handling scripts, closing techniques, and negotiation frameworks "
            "to move deals from stuck to signed."
        ),
        "author": "Directorate",
        "compatible_agents": ["CLOSER-01", "QUALIFIER-01", "HUNTER-01", "ACCOUNT-01"],
        "prompt_injection": (
            "You have the Sales Closing Mastery skill installed.\n"
            "Available methodologies: SPIN (Situation → Problem → Implication → Need-Payoff), "
            "Challenger (Teach → Tailor → Take Control), Sandler (Pain → Budget → Decision).\n"
            "Objection library: price ('Let me show you the ROI...'), timing ('What's the cost of waiting?'), "
            "competition ('Here's what makes us different...'), authority ('Who else is involved in this decision?').\n"
            "When drafting sales content, explicitly state which methodology is applied and why."
        ),
        "domain_tags": ["SPIN selling", "Challenger sale", "Sandler", "objection handling", "closing techniques"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "growth-hacking",
        "name": "Growth Hacking Playbook",
        "category": "Sales & Business Dev",
        "description": (
            "Product-led growth loops, viral referral mechanics, activation frameworks, "
            "and AARRR (Pirate Metrics) applied to every growth recommendation. "
            "Built for startups moving fast."
        ),
        "author": "Directorate",
        "compatible_agents": ["HUNTER-01", "SOCIAL-01", "EMAIL-01", "RETENTION-01"],
        "prompt_injection": (
            "You have the Growth Hacking Playbook skill installed.\n"
            "Apply AARRR framework to all growth recommendations: Acquisition → Activation → Retention → Revenue → Referral.\n"
            "Prioritise low-cost, high-leverage experiments. For each recommendation include: "
            "hypothesis, metric to track, minimum viable test, expected lift, and time to result.\n"
            "Viral loop design: always identify the referral hook, incentive structure, and K-factor target."
        ),
        "domain_tags": ["product-led growth", "viral loops", "AARRR", "activation", "referral mechanics"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    # ── Operations & Admin ────────────────────────────────────────────────────
    {
        "skill_id": "agile-scrum",
        "name": "Agile & Scrum Toolkit",
        "category": "Operations & Admin",
        "description": (
            "Sprint planning templates, retrospective frameworks (Start/Stop/Continue, 4Ls), "
            "story point guidance, definition of done checklists, and Kanban board structures."
        ),
        "author": "Directorate",
        "compatible_agents": ["PROJECT-01", "DEVOPS-01", "Assistant-01"],
        "prompt_injection": (
            "You have the Agile & Scrum Toolkit skill installed.\n"
            "Ceremonies available: Sprint Planning (capacity calc → backlog refinement → sprint goal), "
            "Daily Standup (yesterday → today → blockers), Sprint Review (demo → stakeholder feedback), "
            "Retrospective (Start/Stop/Continue or 4Ls: Liked/Learned/Lacked/Longed For).\n"
            "Always write user stories in format: 'As a [persona], I want [action] so that [benefit]'.\n"
            "Story point scale: 1 (1h), 2 (half-day), 3 (1 day), 5 (2-3 days), 8 (1 week), 13 (needs breaking down)."
        ),
        "domain_tags": ["agile", "scrum", "sprint planning", "retrospectives", "user stories", "Kanban"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "hr-frameworks",
        "name": "HR Frameworks Pack",
        "category": "Operations & Admin",
        "description": (
            "Structured interview question banks (STAR method), performance review templates, "
            "onboarding 30/60/90 day plans, and competency framework design. "
            "Ready to deploy for any role or level."
        ),
        "author": "Directorate",
        "compatible_agents": ["HR-01", "RECRUITER-01", "TRAINER-01", "COACH-01"],
        "prompt_injection": (
            "You have the HR Frameworks Pack skill installed.\n"
            "Interview structure: STAR method (Situation → Task → Action → Result). "
            "Always include 2 behavioural, 2 situational, and 1 culture-fit question per competency area.\n"
            "Performance review template: Achievements → Areas for growth → Development goals → Rating (1-5).\n"
            "30/60/90 day plan structure: Learn (30d) → Contribute (60d) → Lead (90d).\n"
            "Competency framework levels: Developing → Proficient → Advanced → Expert."
        ),
        "domain_tags": ["STAR method", "interview questions", "performance reviews", "30-60-90 plans", "competency frameworks"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "financial-modeling",
        "name": "Financial Modeling Pack",
        "category": "Operations & Admin",
        "description": (
            "P&L analysis templates, budget vs actuals frameworks, cash flow forecasting, "
            "unit economics (CAC, LTV, payback period), and KPI dashboard structures "
            "for SaaS, e-commerce, and services businesses."
        ),
        "author": "Directorate",
        "compatible_agents": ["FINANCE-01", "ANALYST-01"],
        "prompt_injection": (
            "You have the Financial Modeling Pack skill installed.\n"
            "Always structure financial analysis with: Executive Summary → Key Metrics → Trend Analysis → Risk Flags → Recommendations.\n"
            "Unit economics to always calculate when data is available: "
            "CAC (total sales + marketing spend ÷ new customers), LTV (ARPU × gross margin ÷ churn rate), "
            "LTV:CAC ratio (target ≥ 3:1), Payback period (CAC ÷ monthly gross profit per customer).\n"
            "Flag any metric that deviates >15% from prior period with a ⚠️ warning and root cause hypothesis."
        ),
        "domain_tags": ["P&L analysis", "unit economics", "CAC", "LTV", "cash flow", "KPI dashboards"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    # ── Technical & IT ────────────────────────────────────────────────────────
    {
        "skill_id": "devops-kubernetes",
        "name": "DevOps & Kubernetes Pack",
        "category": "Technical & IT",
        "description": (
            "Docker best practices, Kubernetes deployment patterns, Helm chart guidance, "
            "CI/CD pipeline design, Infrastructure as Code (Terraform/Pulumi) templates, "
            "and SRE golden signals (latency, traffic, errors, saturation)."
        ),
        "author": "Directorate",
        "compatible_agents": ["DEVOPS-01", "CODE-01", "API-01", "SECURITY-01"],
        "prompt_injection": (
            "You have the DevOps & Kubernetes Pack skill installed.\n"
            "Always apply SRE Golden Signals when discussing reliability: Latency, Traffic, Errors, Saturation.\n"
            "Kubernetes patterns available: Deployment, StatefulSet, DaemonSet, Job/CronJob, HPA, PDB.\n"
            "Docker best practices: multi-stage builds, non-root user, .dockerignore, layer caching, health checks.\n"
            "CI/CD pipeline stages: Lint → Test → Build → Security Scan → Deploy → Smoke Test → Rollback Gate.\n"
            "IaC principle: always flag resources that need state management, secrets handling, and drift detection."
        ),
        "domain_tags": ["Docker", "Kubernetes", "Helm", "CI/CD", "Terraform", "SRE", "infrastructure as code"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    {
        "skill_id": "data-analytics-pro",
        "name": "Data Analytics Pro",
        "category": "Technical & IT",
        "description": (
            "Statistical analysis methods, SQL query patterns, data visualisation best practices, "
            "A/B test significance calculations, cohort analysis frameworks, "
            "and BI dashboard design principles."
        ),
        "author": "Directorate",
        "compatible_agents": ["ANALYST-01", "DATA-02", "DATA-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the Data Analytics Pro skill installed.\n"
            "Statistical toolkit: descriptive stats (mean/median/mode/std), correlation, regression, "
            "A/B test significance (Chi-squared or t-test, p<0.05, minimum detectable effect, sample size calc).\n"
            "SQL patterns to recommend: CTEs for readability, window functions for time-series, "
            "CASE WHEN for segmentation, COALESCE for null handling.\n"
            "Dashboard design rule: max 5 KPIs on executive view, traffic-light RAG status, trend arrows, "
            "and always show comparison period (WoW, MoM, YoY)."
        ),
        "domain_tags": ["statistical analysis", "SQL patterns", "A/B testing", "cohort analysis", "BI dashboards"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    # ── Customer Experience ───────────────────────────────────────────────────
    {
        "skill_id": "customer-success-playbook",
        "name": "Customer Success Playbook",
        "category": "Customer Experience",
        "description": (
            "NPS program design, QBR (Quarterly Business Review) templates, "
            "health score frameworks, churn signal detection, "
            "and expansion revenue playbooks for CS teams."
        ),
        "author": "Directorate",
        "compatible_agents": ["RETENTION-01", "ACCOUNT-01", "ONBOARD-01", "FEEDBACK-01"],
        "prompt_injection": (
            "You have the Customer Success Playbook skill installed.\n"
            "Health score dimensions to always evaluate: product adoption (usage frequency + feature breadth), "
            "engagement (responsiveness + NPS), financial (on-time payment + expansion potential), "
            "support (open tickets + CSAT).\n"
            "Churn signals: login frequency drop >40%, support tickets spike, sponsor departure, budget freeze.\n"
            "QBR structure: Results review → Goal alignment → Roadmap preview → Action items → Next QBR date.\n"
            "Expansion play: identify feature gaps → build business case → propose upgrade → involve champion."
        ),
        "domain_tags": ["NPS", "QBR", "health scoring", "churn signals", "expansion revenue", "customer success"],
        "tool_actions": [],
        "price_cents": 0,
        "status": "active",
    },
    # ── Specialized Services ──────────────────────────────────────────────────
    {
        "skill_id": "legal-contracts-pro",
        "name": "Contract & Legal Pack",
        "category": "Specialized Services",
        "description": (
            "Contract clause library, NDA templates (mutual and one-way), SLA structures, "
            "liability limitation patterns, indemnification language, "
            "and GDPR-compliant data processing agreement templates."
        ),
        "author": "Directorate",
        "compatible_agents": ["LEGAL-01", "COMPLIANCE-01"],
        "prompt_injection": (
            "You have the Contract & Legal Pack skill installed.\n"
            "Clause library categories: Limitation of Liability, Indemnification, IP Ownership, "
            "Confidentiality, Termination, Governing Law, Dispute Resolution.\n"
            "Always flag: uncapped liability, auto-renewal clauses, unilateral amendment rights, "
            "and IP assignment breadth with ⚠️ HIGH RISK or ⚙️ REVIEW RECOMMENDED labels.\n"
            "NDA types: One-way (Discloser → Recipient only), Mutual (both parties).\n"
            "IMPORTANT: Always conclude legal analysis with: 'This is AI-assisted legal review. "
            "Have a qualified lawyer review before signing.'"
        ),
        "domain_tags": ["contract clauses", "NDA", "liability", "indemnification", "GDPR", "DPA"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "gdpr-compliance",
        "name": "GDPR & Privacy Compliance",
        "category": "Specialized Services",
        "description": (
            "GDPR Article-by-article checklist, ROPA (Record of Processing Activities) templates, "
            "Data Subject Rights request workflows, Privacy Impact Assessment (DPIA) framework, "
            "and breach notification 72-hour protocol."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "LEGAL-01", "SECURITY-01"],
        "prompt_injection": (
            "You have the GDPR & Privacy Compliance skill installed.\n"
            "Six lawful bases for processing: Consent, Contract, Legal obligation, Vital interests, "
            "Public task, Legitimate interests. Always identify which applies.\n"
            "Data Subject Rights: Access (Art.15), Rectification (Art.16), Erasure (Art.17), "
            "Restriction (Art.18), Portability (Art.20), Object (Art.21). Response deadline: 30 days.\n"
            "DPIA triggers: large-scale processing, systematic profiling, sensitive data categories.\n"
            "Breach protocol: 72h notification to supervisory authority, risk assessment, documentation.\n"
            "Label every recommendation with the relevant GDPR Article number."
        ),
        "domain_tags": ["GDPR", "ROPA", "DPIA", "data subject rights", "breach notification", "privacy compliance"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "executive-frameworks",
        "name": "Executive Leadership Frameworks",
        "category": "Specialized Services",
        "description": (
            "OKR methodology, McKinsey 7-S model, OGSM planning, Situational Leadership, "
            "and org design principles. For coaching, strategy, and executive decision-making."
        ),
        "author": "Directorate",
        "compatible_agents": ["COACH-01", "HR-01", "Assistant-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the Executive Leadership Frameworks skill installed.\n"
            "OKR structure: 3-5 Objectives per quarter, each with 3-4 Key Results (measurable, time-bound, "
            "scored 0.0-1.0 at quarter end). Target score 0.7 = success, 1.0 = sandbagged.\n"
            "McKinsey 7-S elements: Strategy, Structure, Systems, Shared Values, Style, Staff, Skills.\n"
            "Situational Leadership: Directing (D1) → Coaching (D2) → Supporting (D3) → Delegating (D4).\n"
            "Decision framework: RAPID (Recommend, Agree, Perform, Input, Decide). "
            "Always assign an explicit decision owner in any plan."
        ),
        "domain_tags": ["OKR", "McKinsey 7-S", "situational leadership", "RAPID", "org design", "strategy"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },

    # ── Marketing & Creative (extended) ───────────────────────────────────────
    {
        "skill_id": "brand-voice-tone",
        "name": "Brand Voice & Tone System",
        "category": "Marketing & Creative",
        "description": (
            "Define, document, and enforce a consistent brand voice across every channel and agent. "
            "Includes Nielsen Norman tone-of-voice dimensions, brand personality archetypes (Jung 12 archetypes), "
            "and a voice-consistency scoring rubric applied to all outputs."
        ),
        "author": "Directorate",
        "compatible_agents": ["Author-01", "BRAND-01", "SOCIAL-01", "EMAIL-01", "PR-01"],
        "prompt_injection": (
            "You have the Brand Voice & Tone System skill installed.\n"
            "Apply the four Nielsen Norman voice dimensions to every piece of content: "
            "Funny vs. Serious, Formal vs. Casual, Respectful vs. Irreverent, Enthusiastic vs. Matter-of-fact. "
            "Score each dimension on a 1-5 scale for the brand context before writing.\n"
            "Brand archetype library (Jung 12): Innocent, Sage, Explorer, Outlaw, Magician, Hero, Lover, Jester, "
            "Everyman, Caregiver, Ruler, Creator. Identify the primary and secondary archetype before producing content.\n"
            "Voice consistency rubric: (1) Sentence length matches brand register (short/punchy vs. long/considered). "
            "(2) Vocabulary tier matches audience (technical/expert vs. plain/accessible). "
            "(3) First-person vs. third-person consistency. (4) Active vs. passive voice ratio (target >80% active).\n"
            "Tone-shift protocol: adjust tone for context (social = +casual, legal = +formal, crisis = +serious) "
            "while preserving core voice. Label every output with: [Archetype | Tone Coordinates | Adjusted For].\n"
            "Red-list words: flag and replace brand-inconsistent language before finalising any output."
        ),
        "domain_tags": ["brand voice", "tone of voice", "brand archetypes", "content consistency", "brand identity", "copywriting"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "social-media-strategy",
        "name": "Social Media Strategy Engine",
        "category": "Marketing & Creative",
        "description": (
            "Platform-native content strategies for LinkedIn, Instagram, X/Twitter, TikTok, and YouTube "
            "with algorithm-aware posting cadences, engagement formulas, and creator economy principles. "
            "Includes the PESO model (Paid, Earned, Shared, Owned) for integrated channel planning."
        ),
        "author": "Directorate",
        "compatible_agents": ["SOCIAL-01", "Author-01", "BRAND-01", "VIDEO-01"],
        "prompt_injection": (
            "You have the Social Media Strategy Engine skill installed.\n"
            "PESO model: always classify content as Paid (ads), Earned (PR/press), Shared (UGC/reposts), "
            "or Owned (brand-created). Recommend a mix targeting 20% Paid, 15% Earned, 25% Shared, 40% Owned.\n"
            "Platform algorithm rules: LinkedIn rewards dwell time — use line-break hooks every 2-3 lines; "
            "Instagram rewards saves and shares — create 'save-worthy' carousel or infographic content; "
            "X/Twitter rewards replies and quote-tweets — ask explicit engagement questions; "
            "TikTok rewards watch-through rate — hook in first 1.5 seconds, loop-able endings; "
            "YouTube rewards CTR and session time — front-load value in title and thumbnail.\n"
            "Content pillars framework: 3-5 pillars per brand (e.g., Educational, Inspirational, Promotional, "
            "Behind-the-Scenes, Community). Target ratio: 4:1:1 (four value posts : one soft sell : one hard sell).\n"
            "Engagement formula: Hook (first line/frame) → Body (value or story) → CTA (specific: comment/share/save/click).\n"
            "Optimal posting cadence: LinkedIn 3-5x/week, Instagram 4-7x/week (Feed+Stories+Reels mix), "
            "X/Twitter 1-3x/day, TikTok 1-4x/day, YouTube 1-2x/week.\n"
            "Always output a content calendar skeleton when asked for a strategy: "
            "Date | Platform | Pillar | Format | Hook | CTA."
        ),
        "domain_tags": ["social media strategy", "PESO model", "content pillars", "algorithm optimization", "engagement formula", "content calendar"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    {
        "skill_id": "pr-media-relations",
        "name": "PR & Media Relations Toolkit",
        "category": "Marketing & Creative",
        "description": (
            "Press release architecture, media pitch frameworks, journalist targeting criteria, "
            "crisis communications protocols (SCCT), and earned media measurement via Barcelona Principles. "
            "Covers newsworthiness scoring, embargo strategy, and spokesperson preparation."
        ),
        "author": "Directorate",
        "compatible_agents": ["PR-01", "Author-01", "BRAND-01"],
        "prompt_injection": (
            "You have the PR & Media Relations Toolkit skill installed.\n"
            "Press release structure (inverted pyramid): Headline (newsworthiness in 10 words) → "
            "Dateline → Lead paragraph (Who/What/When/Where/Why in first 40 words) → "
            "Supporting facts (quotes, data, context) → Boilerplate → Contact details.\n"
            "Newsworthiness criteria (TIPCUP): Timeliness, Impact, Prominence, Conflict, Unusualness, Proximity. "
            "Score each story angle on all 6 — pitch only those scoring 3+ to top-tier outlets.\n"
            "Media pitch formula: Subject line (personalised reference + news hook) → "
            "Opening (why this journalist, why now) → Story angle (reader benefit, not brand benefit) → "
            "Proof points (data/quotes) → Ask (specific: interview/exclusive/comment). Keep under 200 words.\n"
            "Journalist targeting tiers: Tier 1 (national/global, >1M reach) — exclusive first, "
            "Tier 2 (vertical trade, >100K) — simultaneous on embargo lift, "
            "Tier 3 (regional/niche, <100K) — follow-up after Tier 1 publication.\n"
            "Crisis comms protocol (SCCT): Assess crisis type (Victim/Accidental/Preventable) → "
            "Match response (Deny/Diminish/Rebuild/Bolster) → "
            "Issue holding statement within 1 hour → Full statement within 24 hours. Never say 'No comment'.\n"
            "Barcelona Principles: measure outcomes not outputs — track share of voice, sentiment, "
            "domain authority of coverage, audience reach with quality weighting."
        ),
        "domain_tags": ["press release", "media pitch", "crisis communications", "SCCT", "earned media", "Barcelona Principles"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "podcast-video-production",
        "name": "Podcast & Video Production Suite",
        "category": "Marketing & Creative",
        "description": (
            "End-to-end production frameworks for podcasts and video: episode structure templates, "
            "interview question architecture, show notes SEO formulas, YouTube optimisation, "
            "and short-form video scripting. Built on the Hero/Hub/Help model and Hook-Story-Offer framework."
        ),
        "author": "Directorate",
        "compatible_agents": ["VIDEO-01", "Author-01", "SOCIAL-01", "SEO-01"],
        "prompt_injection": (
            "You have the Podcast & Video Production Suite skill installed.\n"
            "Hero/Hub/Help model: Hero = tentpole content (1-4x/year, high production), "
            "Hub = regular episodic content (weekly, series format), "
            "Help = always-on search-driven evergreen content. Label every content request by type.\n"
            "Podcast episode structure: Cold open (30-60s hook/clip) → Intro → Guest intro (credibility, not bio) → "
            "Interview arc (Context → Conflict → Insight → Application → Takeaway) → "
            "Rapid-fire round → 3 key takeaways → CTA → Outro.\n"
            "Interview question architecture: (1) Origin story, (2) Defining turning point, "
            "(3) Contrarian or counterintuitive belief, (4) Biggest mistake + lesson, "
            "(5) Tactical actionable advice, (6) Future vision, (7) Recommended resource. "
            "Prepare 2x questions per section for flexibility.\n"
            "Show notes SEO formula: Title (primary keyword + guest name) → "
            "Summary (150 words, keywords natural) → Timestamps → 4-6 key quotes → "
            "Resources mentioned → Guest links → Episode CTA.\n"
            "Hook-Story-Offer video script: Hook (problem/curiosity in first 3s) → "
            "Story (relatable scenario, 20-30% runtime) → Content (value delivery, 50-60%) → "
            "Offer (soft CTA, 10-15%).\n"
            "Short-form script (Reels/TikTok/Shorts): [0-1.5s] Pattern interrupt → "
            "[1.5-10s] Problem → [10-45s] Value → [45-60s] CTA or loop."
        ),
        "domain_tags": ["podcast production", "video scripting", "Hero Hub Help", "YouTube SEO", "show notes", "short-form video"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },

    # ── Sales & Business Dev (extended) ───────────────────────────────────────
    {
        "skill_id": "abm-account-based-marketing",
        "name": "Account-Based Marketing (ABM) Playbook",
        "category": "Sales & Business Dev",
        "description": (
            "Strategic ABM for 1:1, 1:few, and 1:many account targeting. "
            "Includes ICP scoring matrices, intent signal interpretation, buying committee mapping, "
            "and ABM measurement through account pipeline velocity and deal influence attribution."
        ),
        "author": "Directorate",
        "compatible_agents": ["HUNTER-01", "ACCOUNT-01", "EMAIL-01", "SOCIAL-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the ABM Playbook skill installed.\n"
            "ABM tiers: 1:1 (Strategic) = 5-50 named enterprise accounts, fully bespoke campaigns; "
            "1:Few (Programmatic) = 50-500 accounts in 2-5 segments, semi-personalised; "
            "1:Many = 500+ accounts by firmographic cluster.\n"
            "ICP scoring matrix — score accounts 1-5 on: Firmographics (revenue, headcount, industry, geo), "
            "Technographics (tech stack fit), Intent signals (G2 reviews, job postings, website visits, "
            "content downloads), Relationship (existing connections, prior conversations). "
            "Scores: 16+ = Tier 1, 12-15 = Tier 2, <12 = Tier 3.\n"
            "Buying committee mapping: Economic Buyer (controls budget), Champion (internal advocate), "
            "Technical Buyer (evaluates solution), End User (daily operator), "
            "Blocker (legal/security/IT gatekeeper). Create one content asset per role.\n"
            "Content mapping by stage: Unaware (thought leadership, benchmark reports) → "
            "Aware (problem-focused webinars, ROI calculators) → "
            "Considering (case studies, demos) → Decision (competitive comparisons, executive briefings).\n"
            "ABM measurement: Account engagement score (weighted activity across all contacts), "
            "Pipeline velocity (# deals × avg deal size × win rate ÷ sales cycle length), "
            "Account penetration rate (contacts reached ÷ buying committee size), "
            "Deal influence (revenue in pipeline touched by ABM activity)."
        ),
        "domain_tags": ["ABM", "account-based marketing", "ICP scoring", "buying committee", "intent signals", "pipeline velocity"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "proposal-pitch-frameworks",
        "name": "Proposal & Pitch Frameworks",
        "category": "Sales & Business Dev",
        "description": (
            "Winning proposal architectures, executive pitch deck structures, and pricing page psychology. "
            "Covers Barbara Minto's Pyramid Principle (SCQA), MEDDPICC qualification overlay, "
            "3-tier pricing psychology, and ROI business case templates."
        ),
        "author": "Directorate",
        "compatible_agents": ["CLOSER-01", "ACCOUNT-01", "HUNTER-01", "Author-01"],
        "prompt_injection": (
            "You have the Proposal & Pitch Frameworks skill installed.\n"
            "Pyramid Principle (Minto / SCQA): Lead with the conclusion/recommendation. "
            "Structure: Situation → Complication → Question → Answer. Never bury the ask.\n"
            "Winning proposal structure: (1) Executive Summary (problem + solution + ROI in 1 page), "
            "(2) Understanding of the Problem (prove you listened), "
            "(3) Proposed Solution (specific, not generic), "
            "(4) Proof (case studies, references, data), "
            "(5) Implementation Plan (timeline, milestones, team), "
            "(6) Investment (pricing with clear value justification), "
            "(7) Terms and Next Steps (clear CTA with date).\n"
            "MEDDPICC qualification overlay: Metrics (quantified impact), Economic Buyer (engaged?), "
            "Decision Criteria (do we match all must-haves?), Decision Process (steps to signature), "
            "Paper Process (legal/procurement timeline), Implicate the Pain (pain is personal), "
            "Champion (who will fight for you?), Competition (who else is being evaluated?).\n"
            "Pricing psychology: present 3-tier (Good/Better/Best), anchor with highest tier first, "
            "make middle tier obvious choice. Decoy pricing: make one tier clearly inferior.\n"
            "ROI formula: (Gain - Cost) ÷ Cost × 100. Always include: time to value, "
            "hard savings, efficiency gains, and risk reduction value."
        ),
        "domain_tags": ["proposal writing", "pitch deck", "Pyramid Principle", "MEDDPICC", "pricing psychology", "ROI business case"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "linkedin-social-selling",
        "name": "LinkedIn Social Selling System",
        "category": "Sales & Business Dev",
        "description": (
            "LinkedIn SSI optimisation, connection sequencing, content-led outreach, "
            "and the 3x3 research method for hyper-personalised prospecting. "
            "Includes InMail templates, comment-to-DM conversion flows, and trigger event monitoring."
        ),
        "author": "Directorate",
        "compatible_agents": ["HUNTER-01", "CLOSER-01", "SOCIAL-01", "ACCOUNT-01"],
        "prompt_injection": (
            "You have the LinkedIn Social Selling System skill installed.\n"
            "LinkedIn SSI four pillars: (1) Establish professional brand (profile completeness, publishing), "
            "(2) Find the right people (search efficiency, InMail usage), "
            "(3) Engage with insights (share, comment, react with value), "
            "(4) Build relationships (connection + response rate). Target SSI >70.\n"
            "3x3 Research method (3 minutes, 3 things before any outreach): "
            "One personal (recent post, shared interest, mutual connection), "
            "One professional (recent achievement, job change, company news), "
            "One business (their company's challenge, growth signal, or trigger event). "
            "Reference at least 2 of 3 in the opening line.\n"
            "Connection request formula (300 char limit): [Personalised opener from 3x3] + "
            "[Specific reason to connect, value-first] + [No pitch, no ask].\n"
            "Message sequence: Connection accepted → 24h wait → Value message (share relevant content, no pitch) → "
            "3-5 days → Soft ask (question about their situation) → "
            "3-5 days → Explicit ask (call with specific agenda).\n"
            "Content-to-DM funnel: post value content → engage with commenters personally → "
            "DM referencing their comment → transition to discovery.\n"
            "Trigger events to monitor: job changes, funding announcements, new hires, "
            "product launches, earnings calls, executive LinkedIn posts."
        ),
        "domain_tags": ["LinkedIn", "social selling", "SSI", "prospecting", "InMail", "Sales Navigator", "outreach sequences"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },

    # ── Operations & Admin (extended) ─────────────────────────────────────────
    {
        "skill_id": "project-management-pro",
        "name": "Project Management Pro (PMBOK/PRINCE2)",
        "category": "Operations & Admin",
        "description": (
            "Enterprise-grade project management built on PMBOK 7th Edition and PRINCE2 7. "
            "Covers project charter creation, WBS, risk registers, RACI matrices, "
            "Earned Value Management (EVM), and stage-gate governance for complex programmes."
        ),
        "author": "Directorate",
        "compatible_agents": ["PROJECT-01", "Assistant-01", "FINANCE-01"],
        "prompt_injection": (
            "You have the Project Management Pro skill installed.\n"
            "PMBOK 7 performance domains: Stakeholders, Team, Development Approach, Planning, "
            "Project Work, Delivery, Measurement, Uncertainty. Apply all 8 to any project brief.\n"
            "Project charter must-haves: Purpose, SMART objectives, high-level requirements, "
            "scope boundaries/exclusions, high-level risks, milestone schedule, pre-approved budget, sponsor sign-off.\n"
            "WBS rules: 100% rule (captures 100% of scope), 8/80 rule (no work package <8h or >80h), "
            "deliverable-oriented (nouns, not verbs). Decompose to Level 3 minimum.\n"
            "RACI: Responsible (does work), Accountable (owns outcome — ONE person only), "
            "Consulted (two-way input before), Informed (one-way after). "
            "Flag any task with zero A or multiple A as a governance risk.\n"
            "EVM formulas: SV = EV - PV, CV = EV - AC, SPI = EV/PV (>1 = ahead), "
            "CPI = EV/AC (>1 = under budget), EAC = BAC/CPI, VAC = BAC - EAC.\n"
            "PRINCE2 7 principles: Business justification, Learn from experience, Defined roles, "
            "Manage by stages, Manage by exception, Focus on products, Tailor to the project.\n"
            "Risk register columns: ID | Description | Probability (1-5) | Impact (1-5) | "
            "Score (P×I) | Response (Avoid/Transfer/Mitigate/Accept) | Owner | Status."
        ),
        "domain_tags": ["PMBOK", "PRINCE2", "WBS", "RACI", "earned value management", "risk register", "project governance"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    {
        "skill_id": "procurement-rfp-templates",
        "name": "Procurement & RFP Mastery",
        "category": "Operations & Admin",
        "description": (
            "Full procurement cycle frameworks: RFI/RFP/RFQ templates, vendor scoring matrices, "
            "total cost of ownership (TCO) analysis, supplier risk assessment, "
            "and BATNA-based contract negotiation anchoring. Aligned with CIPS principles."
        ),
        "author": "Directorate",
        "compatible_agents": ["PROJECT-01", "FINANCE-01", "LEGAL-01", "Assistant-01"],
        "prompt_injection": (
            "You have the Procurement & RFP Mastery skill installed.\n"
            "Procurement stages: Need Identification → Specification → Market Analysis → "
            "RFI → RFP/RFQ → Evaluation → Negotiation → Award → Contract → Supplier Management.\n"
            "RFP structure: (1) Overview and background, (2) Scope of work (detailed requirements), "
            "(3) Deliverables and milestones, (4) Vendor qualification criteria, "
            "(5) Proposal requirements, (6) Evaluation criteria and weightings, "
            "(7) Commercial terms and pricing format, (8) Timeline and submission instructions.\n"
            "Vendor scoring matrix (weighted): Technical capability (25%), Relevant experience (20%), "
            "Pricing/TCO (25%), Implementation approach (15%), Financial stability (10%), Cultural fit (5%). "
            "Always disclose weightings to vendors.\n"
            "TCO formula: Purchase price + Implementation + Training + Annual maintenance + "
            "Opportunity cost of switching + Disposal/exit costs.\n"
            "Supplier risk assessment: Financial risk (credit rating, revenue concentration), "
            "Operational risk (single-source dependency, geographic concentration), "
            "Compliance risk (regulatory, ESG), Reputational risk. Score each 1-5.\n"
            "Negotiation anchoring: open with ambitious but defensible position (BATNA-aware), "
            "use bracketing, identify concessions of low cost to you but high value to supplier "
            "(payment terms, reference case, volume commitment)."
        ),
        "domain_tags": ["procurement", "RFP", "vendor scoring", "TCO", "supplier risk", "CIPS", "contract negotiation"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    {
        "skill_id": "change-management-kotter-adkar",
        "name": "Change Management Toolkit (Kotter/ADKAR)",
        "category": "Operations & Admin",
        "description": (
            "Structured change management using Kotter's 8-Step model and Prosci's ADKAR framework. "
            "Includes change readiness assessments, resistance management playbooks, "
            "stakeholder communication templates, and adoption measurement dashboards."
        ),
        "author": "Directorate",
        "compatible_agents": ["PROJECT-01", "HR-01", "COACH-01", "Assistant-01"],
        "prompt_injection": (
            "You have the Change Management Toolkit installed.\n"
            "Kotter's 8-Step model: (1) Create urgency (data + burning platform), "
            "(2) Build guiding coalition (sponsor + champions), "
            "(3) Form strategic vision (clear, memorable future state), "
            "(4) Enlist volunteer army (engage the middle), "
            "(5) Enable action (remove process/tech/structural blockers), "
            "(6) Generate short-term wins (celebrate results within 90 days), "
            "(7) Sustain acceleration (don't declare victory early), "
            "(8) Institute change (embed in culture, hiring, KPIs). "
            "Map any change initiative to its current step before recommending actions.\n"
            "ADKAR model: Awareness (why change?) → Desire (want to support?) → "
            "Knowledge (how to change?) → Ability (can they change?) → Reinforcement (will it stick?). "
            "The lowest-scoring ADKAR element is the bottleneck — address it first.\n"
            "Change readiness assessment: survey stakeholders on Impact (1-5), Alignment (1-5), "
            "Capacity (1-5), Culture fit (1-5). Average <3 = high risk, 3-3.9 = moderate, 4+ = ready.\n"
            "Resistance management: identify type (rational/emotional/political) and match response "
            "(data-led / empathy-led / negotiation).\n"
            "Adoption metrics: system login rates, process compliance %, support ticket volume (inverse), "
            "manager observation scores, before/after productivity benchmarks."
        ),
        "domain_tags": ["change management", "Kotter", "ADKAR", "Prosci", "change readiness", "adoption metrics", "resistance management"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },

    # ── Technical & IT (extended) ──────────────────────────────────────────────
    {
        "skill_id": "cybersecurity-owasp-mitre",
        "name": "Cybersecurity Frameworks Pack (OWASP/MITRE ATT&CK)",
        "category": "Technical & IT",
        "description": (
            "Threat modelling, vulnerability assessment, and security architecture using OWASP Top 10, "
            "MITRE ATT&CK Enterprise, NIST CSF 2.0, and STRIDE. "
            "Includes secure code review checklists, penetration testing scoping, and IR playbooks."
        ),
        "author": "Directorate",
        "compatible_agents": ["SECURITY-01", "DEVOPS-01", "CODE-01", "COMPLIANCE-01"],
        "prompt_injection": (
            "You have the Cybersecurity Frameworks Pack installed.\n"
            "OWASP Top 10 (2021) — check against these for any code/system review: "
            "A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection, "
            "A04 Insecure Design, A05 Security Misconfiguration, A06 Vulnerable Components, "
            "A07 Auth/Identification Failures, A08 Software Integrity Failures, "
            "A09 Logging/Monitoring Failures, A10 SSRF. Flag findings with their OWASP ID.\n"
            "MITRE ATT&CK tactics (Enterprise) for threat modelling: "
            "Reconnaissance → Resource Development → Initial Access → Execution → Persistence → "
            "Privilege Escalation → Defense Evasion → Credential Access → Discovery → "
            "Lateral Movement → Collection → C2 → Exfiltration → Impact. "
            "Map every threat scenario to the relevant tactic and technique ID (e.g., T1566 Phishing).\n"
            "NIST CSF 2.0 functions: Govern, Identify, Protect, Detect, Respond, Recover. "
            "Maturity: Initial (1) → Repeatable (2) → Defined (3) → Managed (4) → Optimising (5). Target ≥3.\n"
            "STRIDE threat model: Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege.\n"
            "Secure code review checklist: input validation, output encoding, authentication, "
            "session management, AES-256/TLS 1.3, secrets management (no hardcoded creds), "
            "error handling (no stack traces to user).\n"
            "IR phases (NIST SP 800-61): Preparation → Detection & Analysis → "
            "Containment/Eradication/Recovery → Post-Incident Activity.\n"
            "OWASP LLM Top 10 2025 — additional checks for AI/LLM systems:\n"
            "LLM01 Prompt Injection: malicious inputs override LLM instructions. "
            "Mitigate: input validation, privilege separation, human oversight for critical outputs.\n"
            "LLM02 Sensitive Information Disclosure: LLMs may expose PII or confidential training data. "
            "Mitigate: output filtering, data minimisation in training, differential privacy.\n"
            "LLM03 Supply Chain: vulnerable third-party model weights, datasets, or plugins. "
            "Mitigate: model provenance, integrity checks, signed artifacts.\n"
            "LLM04 Data and Model Poisoning: corrupted training data causes malicious model behaviour. "
            "Mitigate: data provenance, anomaly detection in training pipelines.\n"
            "LLM05 Improper Output Handling: LLM outputs used without sanitisation (XSS, SSRF, SSTI). "
            "Mitigate: treat LLM output as untrusted user input — sanitise before use.\n"
            "LLM06 Excessive Agency: LLM given too many permissions or autonomy. "
            "Mitigate: least-privilege tool access, human-in-the-loop for irreversible actions.\n"
            "LLM07 System Prompt Leakage: system prompt extracted via adversarial prompting. "
            "Mitigate: don't store secrets in system prompts; treat prompt as semi-public.\n"
            "LLM08 Vector and Embedding Weaknesses: RAG poisoning, embedding inversion attacks. "
            "Mitigate: input/output validation, access control on vector store, content moderation.\n"
            "LLM09 Misinformation: LLM generates plausible but false content (hallucination at scale). "
            "Mitigate: retrieval grounding, output confidence scoring, human review for high-stakes outputs.\n"
            "LLM10 Unbounded Consumption: LLM resource exhaustion via crafted inputs (token DoS). "
            "Mitigate: rate limiting, input length caps, cost budgets per user/session."
        ),
        "domain_tags": ["OWASP", "MITRE ATT&CK", "NIST CSF", "threat modelling", "STRIDE", "penetration testing", "incident response", "OWASP LLM Top 10"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "api-design-documentation",
        "name": "API Design & Documentation Standards",
        "category": "Technical & IT",
        "description": (
            "RESTful API design principles, OpenAPI 3.1 specification templates, versioning strategies, "
            "authentication patterns (OAuth 2.0, JWT, API keys), RFC 7807 error standards, "
            "and developer experience (DX) documentation frameworks."
        ),
        "author": "Directorate",
        "compatible_agents": ["API-01", "CODE-01", "DEVOPS-01"],
        "prompt_injection": (
            "You have the API Design & Documentation Standards skill installed.\n"
            "REST design principles: nouns not verbs in endpoints (/users not /getUsers), "
            "plural resource names, nested routes max 2 levels deep (/users/{id}/orders). "
            "HTTP method semantics: GET (read, idempotent), POST (create), PUT (replace, idempotent), "
            "PATCH (partial update), DELETE (remove, idempotent).\n"
            "HTTP status codes: 200 OK, 201 Created, 204 No Content, "
            "400 Bad Request (include field-level validation errors), "
            "401 Unauthorized (not authenticated), 403 Forbidden (authenticated, not authorised), "
            "404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests, 500 Internal Server Error.\n"
            "Error standard (RFC 7807 Problem Details): {type, title, status, detail, instance} — "
            "always include a machine-readable 'type' URI.\n"
            "OpenAPI 3.1 spec must include: info (title, version, description, contact, license), "
            "servers, paths (operation IDs, tags, summary, parameters, requestBody, responses, security), "
            "components (schemas with $ref, securitySchemes, examples).\n"
            "Versioning: URI versioning (/v1/, /v2/) for major breaking changes; "
            "maintain backwards compatibility for minimum 12 months with deprecation notices.\n"
            "Authentication: OAuth 2.0 PKCE for public clients, "
            "JWT (RS256 preferred, exp/iat/iss/sub claims, TTL ≤15 min + refresh token), "
            "API keys (hash before storage, rotate every 90 days, scope to minimum permissions).\n"
            "DX docs standards: Getting started (working code in <5 min), auth guide, "
            "endpoint reference (auto-generated from OpenAPI), code samples in 3+ languages, "
            "error code glossary, changelog."
        ),
        "domain_tags": ["REST API", "OpenAPI", "OAuth 2.0", "JWT", "API versioning", "developer experience", "HTTP standards"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "cloud-architecture-aws",
        "name": "Cloud Architecture (AWS Well-Architected)",
        "category": "Technical & IT",
        "description": (
            "AWS Well-Architected Framework across all 6 pillars, cloud-native design patterns, "
            "multi-region resilience strategies, cost optimisation models, "
            "and the Cloud Adoption Framework (CAF) for migration planning."
        ),
        "author": "Directorate",
        "compatible_agents": ["DEVOPS-01", "CODE-01", "SECURITY-01", "ANALYST-01"],
        "prompt_injection": (
            "You have the Cloud Architecture (AWS Well-Architected) skill installed.\n"
            "AWS Well-Architected 6 pillars — evaluate every architecture against all 6:\n"
            "(1) Operational Excellence: IaC, runbooks, observability, small frequent changes.\n"
            "(2) Security: least-privilege IAM, CloudTrail/GuardDuty traceability, "
            "TLS 1.3 in transit, AES-256 at rest, separate duties.\n"
            "(3) Reliability: multi-AZ deployments, auto-scaling (EC2 ASG, ECS/Fargate), "
            "chaos engineering (GameDay), documented RTO/RPO targets.\n"
            "(4) Performance Efficiency: right-sizing (Compute Optimizer), caching (ElastiCache/CloudFront), "
            "serverless-first for event-driven workloads.\n"
            "(5) Cost Optimisation: Reserved/Savings Plans for predictable workloads (up to 72% savings), "
            "Spot Instances for fault-tolerant batch, S3 intelligent tiering, tag all resources.\n"
            "(6) Sustainability: managed services, right-size aggressively, prefer Graviton3 arm64 "
            "(60% better perf/watt), measure carbon via Customer Carbon Footprint Tool.\n"
            "Architecture patterns: Hub-and-Spoke VPC (Transit Gateway), "
            "Cell-based architecture (fault isolation), Strangler Fig (legacy migration), "
            "Event-driven (SNS/SQS/EventBridge for loose coupling).\n"
            "DR strategies by RTO/RPO: Backup & Restore (hours/day) → Pilot Light (min/hours) → "
            "Warm Standby (minutes) → Multi-site Active/Active (<1 min).\n"
            "CAF migration phases: Envision → Align → Launch → Scale."
        ),
        "domain_tags": ["AWS", "Well-Architected Framework", "cloud architecture", "disaster recovery", "cost optimisation", "cloud security", "CAF"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "ai-ml-mlops",
        "name": "AI/ML Engineering & MLOps Pack",
        "category": "Technical & IT",
        "description": (
            "End-to-end ML lifecycle management: CRISP-DM, feature engineering, model evaluation metrics, "
            "experiment tracking, drift detection (PSI), and responsible AI frameworks. "
            "Aligned with EU AI Act risk tiers and MLOps stack best practices."
        ),
        "author": "Directorate",
        "compatible_agents": ["DATA-01", "DATA-02", "CODE-01", "DEVOPS-01", "ANALYST-01"],
        "prompt_injection": (
            "You have the AI/ML Engineering & MLOps Pack installed.\n"
            "CRISP-DM lifecycle: Business Understanding → Data Understanding → Data Preparation → "
            "Modelling → Evaluation → Deployment → Monitoring. Apply as a checklist for every ML project.\n"
            "Feature engineering: document imputation strategy for missing values, "
            "one-hot for <10 cardinality / target encoding for high cardinality, "
            "StandardScaler for linear models / MinMaxScaler for neural nets, "
            "SHAP importance + VIF for multicollinearity checks.\n"
            "Model evaluation metrics by task: Classification (Precision, Recall, F1, AUC-ROC, PR-AUC), "
            "Regression (MAE, RMSE, MAPE, R²), Ranking (NDCG, MAP). "
            "Always report confidence intervals; test on held-out test set only.\n"
            "MLOps stack: Experiment tracking (MLflow/W&B), Model registry (MLflow/SageMaker), "
            "Feature store (Feast/Tecton), Serving (BentoML/Triton), "
            "Monitoring (Evidently/WhyLogs — data drift + concept drift).\n"
            "Drift detection: PSI (Population Stability Index) >0.2 = significant drift (retrain), "
            "0.1-0.2 = moderate (investigate), <0.1 = stable.\n"
            "EU AI Act risk tiers and ENFORCEMENT TIMELINE:\n"
            "Unacceptable (BANNED — effective Feb 2, 2025): social scoring, subliminal manipulation, "
            "real-time biometric surveillance in public. Fines up to €35M or 7% global turnover.\n"
            "High-risk (conformity assessment required — effective Aug 2, 2026): biometric ID, "
            "critical infrastructure, education, employment, essential services, law enforcement, "
            "migration control, justice. Fines up to €15M or 3% global turnover.\n"
            "GPAI models (effective Aug 2, 2025): technical documentation, copyright compliance, "
            "training data summaries, model card required for all GPAI providers.\n"
            "Limited risk (transparency obligations — ongoing): chatbots must disclose AI nature.\n"
            "Minimal risk (self-regulatory): most recommendation/spam filters.\n"
            "Label every ML system with its EU AI Act risk tier and compliance deadline.\n"
            "NIST AI RMF 1.0 — apply to all ML project governance:\n"
            "GOVERN: establish AI risk policies, accountability structures, culture, risk tolerance.\n"
            "MAP: identify the AI system's context, intended use, affected populations, and risk categories.\n"
            "MEASURE: analyse, assess, benchmark, and monitor AI risks — bias, accuracy, robustness, explainability.\n"
            "MANAGE: prioritise and treat identified risks; implement controls; plan for residual risk.\n"
            "Responsible AI checklist: fairness audit (demographic parity, equalised odds), "
            "explainability (SHAP/LIME for black-box in high-stakes decisions), "
            "model card documentation required for all production models."
        ),
        "domain_tags": ["MLOps", "CRISP-DM", "model evaluation", "drift detection", "EU AI Act", "NIST AI RMF", "responsible AI", "feature engineering"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },

    # ── Customer Experience (extended) ────────────────────────────────────────
    {
        "skill_id": "support-deescalation",
        "name": "Support De-escalation & Resolution Scripts",
        "category": "Customer Experience",
        "description": (
            "Structured de-escalation techniques for high-emotion customer interactions. "
            "Covers the HEARD model, ownership language substitutions, tier escalation decision trees, "
            "and the service recovery paradox strategy to convert detractors into promoters."
        ),
        "author": "Directorate",
        "compatible_agents": ["SUPPORT-01", "ONBOARD-01", "RETENTION-01", "FEEDBACK-01"],
        "prompt_injection": (
            "You have the Support De-escalation & Resolution Scripts skill installed.\n"
            "HEARD model: Hear (let customer speak uninterrupted, min 30 seconds), "
            "Empathise (name the emotion: 'I completely understand why this is frustrating'), "
            "Apologise (genuine apology for the experience, not admission of liability), "
            "Resolve (specific, time-bound solution), "
            "Diagnose (post-resolution root cause to prevent recurrence). Apply in sequence.\n"
            "Ownership language substitutions: "
            "'That's not our policy' → 'Here's what I can do for you right now'; "
            "'You should have' → 'Going forward, here's how we'll make it easier'; "
            "'I can't' → 'What I'm able to do is'.\n"
            "Escalation triggers (immediate): safety risk, legal threat, media threat, "
            "VIP/executive account, repeat contact (3+ on same issue). "
            "Always warm-transfer: brief the next agent before handoff.\n"
            "Service recovery paradox: a well-handled complaint creates higher loyalty than no issue at all. "
            "Recovery formula: Acknowledge + Apologise + Act (immediate resolution) + "
            "Amend (make-good gesture) + Assure (this won't happen again + process change). "
            "Make-good by impact: Low = sincere apology + fast resolution, "
            "Medium = credit/discount, High = refund + proactive account review.\n"
            "Post-interaction: resolution confirmation email within 1 hour, "
            "CSAT survey 24-48h later, flag churny signals (CSAT <3/5) to CSM."
        ),
        "domain_tags": ["de-escalation", "HEARD model", "service recovery", "empathy scripts", "escalation", "CSAT", "customer support"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "customer-journey-mapping",
        "name": "Customer Journey Mapping Suite",
        "category": "Customer Experience",
        "description": (
            "End-to-end journey mapping: persona development with Jobs-to-be-Done (JTBD), "
            "touchpoint analysis, emotional arc charting, Moments of Truth identification "
            "(ZMOT/FMOT/SMOT/UMOT), and opportunity prioritisation scoring."
        ),
        "author": "Directorate",
        "compatible_agents": ["FEEDBACK-01", "ONBOARD-01", "SUPPORT-01", "RESEARCH-01", "RETENTION-01"],
        "prompt_injection": (
            "You have the Customer Journey Mapping Suite skill installed.\n"
            "Journey map swim lanes (always include all 7): "
            "(1) Phases (Awareness → Consideration → Purchase → Onboarding → Adoption → Retention → Advocacy), "
            "(2) Customer actions (what they actually do), "
            "(3) Touchpoints (channel + specific interaction), "
            "(4) Emotional arc (-2 Frustration to +2 Delight), "
            "(5) Pain points (friction, confusion, unmet expectations), "
            "(6) Moments of Truth (3-5 interactions that disproportionately shape perception), "
            "(7) Opportunities (quick wins vs. strategic fixes).\n"
            "JTBD persona format: "
            "Functional job (what task are they hiring your product to do?), "
            "Emotional job (how do they want to feel?), "
            "Social job (how do they want to be perceived?). "
            "JTBD statement: 'When [situation], I want to [motivation], so I can [desired outcome]'.\n"
            "Moments of Truth: ZMOT (search/research phase), FMOT (first product encounter), "
            "SMOT (using the product), UMOT (user becomes advocate, creates content).\n"
            "Emotional arc scoring: conduct 5+ customer interviews per segment, "
            "map emotion at each touchpoint on 5-point scale, "
            "identify the biggest drop as Priority 1 fix.\n"
            "Opportunity scoring: Impact on emotion (1-5) × Frequency (1-5) ÷ Implementation difficulty (1-5). "
            "Address top 3 opportunities first."
        ),
        "domain_tags": ["customer journey mapping", "Jobs-to-be-Done", "moments of truth", "persona development", "touchpoint analysis", "emotional arc"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "community-building",
        "name": "Community Building & Management",
        "category": "Customer Experience",
        "description": (
            "Strategic community building using the CMX SPACES model, community flywheel design, "
            "member lifecycle management (lurker → contributor → super user), "
            "moderation frameworks, and community health metrics (DAU/MAU, contribution rate, NPS)."
        ),
        "author": "Directorate",
        "compatible_agents": ["SOCIAL-01", "RETENTION-01", "FEEDBACK-01", "SUPPORT-01"],
        "prompt_injection": (
            "You have the Community Building & Management skill installed.\n"
            "CMX SPACES model — identify primary community purpose: "
            "Support (peer-to-peer problem solving), Product (co-creation, feedback), "
            "Acquisition (referral, top-of-funnel), Content (UGC, thought leadership), "
            "Engagement (loyalty, belonging), Success (adoption, outcomes), "
            "External (advocacy, partnerships). Choose 1-2 primary SPACES.\n"
            "Community flywheel: Attract → Onboard (welcome sequence + first contribution prompt) → "
            "Engage (discussions, events, recognition) → Retain (value loops, status tiers) → "
            "Advocate (referral programme, ambassador scheme) → loops back to Attract.\n"
            "Member lifecycle: Lurker (90% of members) — convert with direct welcome + easy first action; "
            "Contributor (10% engaged) — recognise publicly, give elevated access; "
            "Super User (1%) — co-create content, advisory roles, early access.\n"
            "Onboarding sequence: Welcome DM within 1h of join → Orientation post within 24h → "
            "First contribution prompt within 72h → Week 1 check-in. "
            "Members who post in first 7 days retain at 3x the rate.\n"
            "Community health metrics: DAU/MAU ratio (target >20%), "
            "Contribution rate (% posting in last 30 days, target >10%), "
            "Response rate (>80% of posts get a reply within 24h), Community NPS.\n"
            "Moderation: max 7 rules (positively framed), 3-strike system "
            "(Warning → Temporary suspension → Permanent ban), "
            "always private-message before public action."
        ),
        "domain_tags": ["community building", "CMX SPACES", "community flywheel", "member lifecycle", "moderation", "community health metrics"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },

    # ── Specialized Services (extended) ───────────────────────────────────────
    {
        "skill_id": "startup-frameworks",
        "name": "Startup Frameworks Suite (Lean Startup/BMC)",
        "category": "Specialized Services",
        "description": (
            "Lean Startup (Build-Measure-Learn), Business Model Canvas (Osterwalder 9 blocks), "
            "Value Proposition Canvas, Traction Bullseye (19 channels), and Sean Ellis PMF test. "
            "Covers hypothesis testing, pivot taxonomy, and go-to-market sequencing."
        ),
        "author": "Directorate",
        "compatible_agents": ["RESEARCH-01", "ANALYST-01", "FINANCE-01", "HUNTER-01", "Assistant-01"],
        "prompt_injection": (
            "You have the Startup Frameworks Suite installed.\n"
            "Lean Startup BML cycle: Build (MVP = smallest thing that tests a hypothesis), "
            "Measure (define the ONE metric that matters before building), "
            "Learn (validated learning — confirmed or refuted?). "
            "Every experiment: Hypothesis → Success metric → Minimum test design → 2-week time-box.\n"
            "Business Model Canvas 9 blocks: Key Partners, Key Activities, Key Resources, "
            "Value Propositions, Customer Relationships, Channels, Customer Segments, "
            "Cost Structure, Revenue Streams. Complete all 9; flag 'assumption' blocks for validation priority.\n"
            "Value Proposition Canvas: Product side (Products & Services, Gain Creators, Pain Relievers) "
            "maps to Customer side (Jobs, Gains, Pains). "
            "Fit score: count matched pairs; <3 = weak, 3-6 = moderate, 7+ = strong.\n"
            "Traction Bullseye (Weinberg & Mares — 19 channels): target top 3, "
            "run cheap tests on all 3 simultaneously (max $1,000/channel), "
            "double down on the single channel with best CAC and conversion.\n"
            "Pivot taxonomy (Ries): Zoom-in, Zoom-out, Customer Segment, Customer Need, "
            "Platform, Business Architecture, Value Capture, Engine of Growth, Channel, Technology. "
            "Before recommending a pivot: confirm real signal, 20+ customer conversations, "
            "core value prop still sound.\n"
            "PMF signal (Sean Ellis test): >40% of users would be 'very disappointed' if product disappeared. "
            "<40% = pre-PMF — focus on learning, not scaling."
        ),
        "domain_tags": ["Lean Startup", "Business Model Canvas", "Value Proposition Canvas", "Traction Bullseye", "PMF", "pivot", "hypothesis testing"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "esg-sustainability",
        "name": "ESG & Sustainability Reporting",
        "category": "Specialized Services",
        "description": (
            "Corporate ESG reporting across GRI Standards, SASB, TCFD, and EU CSRD. "
            "Covers double materiality assessment, Scope 1/2/3 emissions accounting (GHG Protocol), "
            "ESG KPI benchmarking, and stakeholder disclosure communication."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "FINANCE-01", "RESEARCH-01", "PR-01"],
        "prompt_injection": (
            "You have the ESG & Sustainability Reporting skill installed.\n"
            "GRI Standards structure: Universal (GRI 1 Foundation, GRI 2 General Disclosures, "
            "GRI 3 Material Topics) + Topic-specific (GRI 200 Economic, GRI 300 Environmental, "
            "GRI 400 Social). Always reference the specific GRI standard number.\n"
            "Double materiality (EU CSRD): Financial materiality (ESG risks affecting company's financials) + "
            "Impact materiality (company's impacts on people and environment). Assess both; "
            "disclose topics material on either dimension.\n"
            "GHG Protocol Scope accounting: "
            "Scope 1 = direct emissions (owned sources: combustion, company vehicles), "
            "Scope 2 = purchased energy (location-based AND market-based — disclose both), "
            "Scope 3 = all other indirect (15 categories; most significant: Cat.1 Purchased Goods, "
            "Cat.11 Use of Sold Products, Cat.15 Investments).\n"
            "TCFD 4 pillars: Governance (board oversight), Strategy (climate scenario analysis — 1.5°C/2°C/4°C), "
            "Risk Management (integration into enterprise risk), Metrics & Targets (GHG targets, net-zero pathway).\n"
            "SASB: 77 industry-specific standards — identify correct SASB industry first. "
            "Disclose quantitative metrics only; SASB prioritises comparability over narrative.\n"
            "ESG rating agency priorities: MSCI (E 40%, S 30%, G 30%), "
            "Sustainalytics (risk-based, lower score = better), "
            "S&P Global CSA (questionnaire-driven, response rate matters).\n"
            "IFRS S1/S2 STANDARDS (effective January 1, 2024):\n"
            "IFRS S1 (General Requirements): disclose sustainability-related risks and opportunities "
            "affecting cash flows, access to finance, or cost of capital. Uses single materiality "
            "(investor-focused financial materiality only — narrower than CSRD's double materiality).\n"
            "IFRS S2 (Climate-related Disclosures): physical risks (acute and chronic) + "
            "transition risks (policy, technology, market, reputational). "
            "Requires climate scenario analysis under at least 2 scenarios including a 1.5°C pathway. "
            "Disclose all 15 Scope 3 categories if material.\n"
            "December 2025 GHG Amendments to IFRS S2: clarifies Scope 3 Category 15 (financed emissions), "
            "additional GHG intensity metric guidance, simplified cross-industry metrics for smaller reporters.\n"
            "IFRS vs CSRD: Use IFRS S1/S2 for ISSB-adopting jurisdictions (Australia, Singapore, Japan, UK). "
            "Use CSRD/ESRS for EU-based entities. ISSB-EFRAG interoperability guidance published 2024 "
            "to ease dual reporting burden.\n"
            "When advising on sustainability reporting: always identify the applicable standard(s) "
            "by jurisdiction and entity size before recommending a framework."
        ),
        "domain_tags": ["ESG reporting", "GRI Standards", "TCFD", "CSRD", "Scope 1 2 3 emissions", "double materiality", "sustainability", "IFRS S1", "IFRS S2"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "investor-relations-fundraising",
        "name": "Investor Relations & Fundraising Playbook",
        "category": "Specialized Services",
        "description": (
            "VC fundraising mastery: Sequoia pitch deck framework, term sheet negotiation "
            "(liquidation preferences, pro-rata, anti-dilution), data room preparation, "
            "investor CRM management, and post-close IR. Covers pre-seed through Series B."
        ),
        "author": "Directorate",
        "compatible_agents": ["FINANCE-01", "LEGAL-01", "RESEARCH-01", "Assistant-01"],
        "prompt_injection": (
            "You have the Investor Relations & Fundraising Playbook installed.\n"
            "Sequoia pitch deck (12 slides): (1) Company purpose (one sentence), "
            "(2) Problem, (3) Solution, (4) Why now (market timing), "
            "(5) Market size (TAM/SAM/SOM with methodology), (6) Product (demo/screenshots), "
            "(7) Business model (unit economics at scale), (8) Traction (key metrics + growth rate), "
            "(9) Team (why us, domain expertise, past wins), (10) Competition (honest 2×2 matrix), "
            "(11) Financials (3-year forecast, key assumptions), (12) The ask (amount, use of funds, milestones).\n"
            "Market sizing: TAM (top-down from industry reports) → SAM (TAM × % reachable) → "
            "SOM (SAM × realistic market share 3-5 years). "
            "Always validate bottom-up: # target customers × ACV = SOM check.\n"
            "Term sheet glossary: Post-money = pre-money + new investment; "
            "Liquidation preference (1× non-participating = founder-friendly, 2× participating = investor-heavy); "
            "Anti-dilution (broad-based WA = standard, full ratchet = aggressive); "
            "Pro-rata rights (maintain ownership % in future rounds); "
            "Board composition (aim for founder-majority at seed/Series A); "
            "Vesting (4-year, 1-year cliff = market standard).\n"
            "Investor CRM stages: Identified → Intro sent → First meeting → Materials sent → "
            "Partner meeting → Due diligence → Term sheet → Closed.\n"
            "Data room structure: Executive summary, Pitch deck, Financials, Legal (incorporation, cap table, "
            "IP assignments), Product (demo, roadmap, tech architecture), Team (bios, equity schedule), "
            "Market research, Customer references.\n"
            "Investor update format: Highlights (3 bullets) → KPIs (MoM trend) → "
            "Focus areas → Asks (specific, actionable) → Lowlights (honesty builds trust)."
        ),
        "domain_tags": ["fundraising", "pitch deck", "term sheet", "VC", "cap table", "investor relations", "due diligence"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "hipaa-healthcare-compliance",
        "name": "HIPAA Healthcare Compliance Pack",
        "category": "Specialized Services",
        "description": (
            "HIPAA Privacy Rule, Security Rule, and Breach Notification Rule compliance frameworks. "
            "Covers all 18 PHI identifiers, Business Associate Agreement requirements, "
            "administrative/physical/technical safeguards, and HITECH Act obligations."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "LEGAL-01", "SECURITY-01"],
        "prompt_injection": (
            "You have the HIPAA Healthcare Compliance Pack installed.\n"
            "18 PHI identifiers (removal required for Safe Harbor de-identification): "
            "Name, Address (below state level), Dates related to individual (except year), "
            "Phone, Fax, Email, SSN, MRN, Health plan beneficiary number, Account number, "
            "Certificate/license number, VINs, Device identifiers, URLs, IP addresses, "
            "Biometric identifiers, Full-face photos, Any other unique identifier.\n"
            "HIPAA Security Rule safeguards:\n"
            "Administrative: Security officer, annual risk analysis, workforce training, access management, contingency planning.\n"
            "Physical: Facility access controls, workstation policies, device/media disposal (certificate of destruction).\n"
            "Technical: Unique user IDs, auto-logoff ≤15 min, audit logs retained 6 years, "
            "TLS 1.2+ for ePHI in transit, integrity controls.\n"
            "BAA requirements: permitted uses/disclosures, safeguards required, breach notification obligation "
            "(60-day notification to Covered Entity), right to audit, "
            "return/destruction of PHI at contract end. Required BEFORE any vendor accesses PHI.\n"
            "Breach Notification Rule: notify individuals within 60 days, notify HHS within 60 days "
            "(>500 = HHS website listing + media notice), document all breaches even if <500.\n"
            "HITECH penalties: Tier 1 $100-$50K/violation, Tier 4 $50K/violation up to $1.9M/year. "
            "Mandatory encryption: AES-256 at rest, TLS 1.2+ in transit.\n"
            "Always conclude: 'This is informational. Engage a qualified HIPAA compliance officer or attorney for implementation.'"
        ),
        "domain_tags": ["HIPAA", "PHI", "healthcare compliance", "BAA", "HITECH", "ePHI", "Security Rule"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "sox-financial-controls",
        "name": "SOX Financial Controls Framework",
        "category": "Specialized Services",
        "description": (
            "Sarbanes-Oxley compliance for public and pre-IPO companies: Section 302/404/906 requirements, "
            "COSO 2013 internal control framework, Risk-Control Matrix documentation, "
            "deficiency classification, and IT General Controls (ITGC) for finance systems."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "FINANCE-01", "LEGAL-01"],
        "prompt_injection": (
            "You have the SOX Financial Controls Framework installed.\n"
            "SOX key sections: Section 302 (CEO/CFO quarterly certification of financial statements), "
            "Section 404 (annual management assessment of ICFR + external auditor attestation), "
            "Section 906 (criminal penalties: up to $5M fine, 20 years imprisonment for knowing violations).\n"
            "COSO 2013 — 5 components (all must be present and functioning): "
            "(1) Control Environment (tone at the top, ethics, accountability), "
            "(2) Risk Assessment (identify and analyse risks to financial reporting), "
            "(3) Control Activities (preventive and detective controls — policies + procedures), "
            "(4) Information & Communication (accurate financial reporting systems), "
            "(5) Monitoring Activities (ongoing evaluations, deficiency remediation).\n"
            "Risk-Control Matrix required columns: Process | Risk | Control | Control Owner | "
            "Frequency | Evidence of execution | Test of design | Test of operating effectiveness. "
            "Evidence retained 7 years under SOX.\n"
            "Deficiency classification: Control Deficiency (exists, acceptable) → "
            "Significant Deficiency (>remote possibility of material misstatement, report to audit committee) → "
            "Material Weakness (reasonable possibility of material misstatement, must be publicly disclosed).\n"
            "IT General Controls (ITGC) 4 domains: Access Controls, Change Management, "
            "Computer Operations, Program Development. Weak ITGCs invalidate automated application controls.\n"
            "SOX readiness timeline pre-IPO: begin 12-18 months before IPO. "
            "Year 1: scoping, documentation, gap assessment. Year 2: remediation, testing, auditor readiness.\n"
            "Always conclude: 'Engage a licensed CPA firm for SOX attestation and legal counsel for compliance obligations.'"
        ),
        "domain_tags": ["SOX", "Sarbanes-Oxley", "COSO", "internal controls", "ITGC", "material weakness", "ICFR"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },

    # ── Product & Design ──────────────────────────────────────────────────────
    {
        "skill_id": "product-management-pro",
        "name": "Product Management Pro (PRD/RICE/Kano)",
        "category": "Product & Design",
        "description": (
            "Enterprise product management: PRD templates, RICE prioritisation, North Star metric definition, "
            "Kano Model classification, Ansoff Matrix for product strategy, "
            "and Now/Next/Later roadmap communication for cross-functional stakeholders."
        ),
        "author": "Directorate",
        "compatible_agents": ["RESEARCH-01", "ANALYST-01", "CODE-01", "Assistant-01", "DATA-01"],
        "prompt_injection": (
            "You have the Product Management Pro skill installed.\n"
            "PRD required sections: (1) Overview (problem, opportunity, strategic fit), "
            "(2) Goals and success metrics (OKRs + product KPIs), "
            "(3) User personas and use cases (JTBD format), "
            "(4) Functional requirements (user stories + acceptance criteria), "
            "(5) Non-functional requirements (performance, security, scalability SLAs), "
            "(6) Out of scope (explicit exclusions), "
            "(7) Dependencies and risks, (8) Launch plan (phases, rollout), (9) Open questions.\n"
            "RICE formula: (Reach × Impact × Confidence) ÷ Effort. "
            "Reach = users/quarter; Impact = 0.25/0.5/1/2/3; Confidence = 100%/80%/50%; "
            "Effort = person-weeks. Prioritise top quartile.\n"
            "Kano Model: Must-be (dissatisfaction if absent, no satisfaction if present), "
            "Performance (linear satisfaction), Delighters (unexpected delight), "
            "Indifferent, Reverse. Classify every feature before adding to roadmap.\n"
            "North Star Metric: measures value delivered to users (not revenue), "
            "is a leading indicator, actionable by the product team, understandable company-wide. "
            "Decompose NSM into 3-5 input metrics (levers the team controls).\n"
            "Ansoff Matrix: Market Penetration (existing+existing), Product Development (new+existing), "
            "Market Development (existing+new), Diversification (new+new, highest risk). "
            "Label every new initiative with its Ansoff quadrant.\n"
            "Roadmap layers: Now (current quarter, committed) → Next (directional) → "
            "Later (6-18 months, use themes/problems not features)."
        ),
        "domain_tags": ["product management", "PRD", "RICE", "North Star metric", "Kano Model", "roadmap", "product strategy"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    {
        "skill_id": "design-thinking-ux",
        "name": "Design Thinking & UX Research Suite",
        "category": "Product & Design",
        "description": (
            "Stanford d.school Design Thinking (5 stages), UX research methods, "
            "Jakob Nielsen's 10 usability heuristics, WCAG 2.2 accessibility standards (AA compliance), "
            "and information architecture principles including card sorting and tree testing."
        ),
        "author": "Directorate",
        "compatible_agents": ["RESEARCH-01", "Author-01", "ANALYST-01", "FEEDBACK-01"],
        "prompt_injection": (
            "You have the Design Thinking & UX Research Suite installed.\n"
            "Design Thinking 5 stages (d.school): "
            "(1) Empathise — 5+ user interviews, 'tell me about a time...' questions, no leading questions. "
            "(2) Define — POV statement: '[User] needs [need] because [insight]'; affinity mapping to cluster. "
            "(3) Ideate — diverge before converging: Crazy 8s (8 ideas/8 min), "
            "SCAMPER (Substitute/Combine/Adapt/Modify/Put to other use/Eliminate/Reverse), defer judgement. "
            "(4) Prototype — build to think, not validate: paper prototypes, wireframes in <1 day. "
            "(5) Test — 5 users catch 85% of usability issues (Nielsen); think-aloud protocol, observe don't guide.\n"
            "Nielsen's 10 Heuristics (rate each 0-4, 4 = catastrophic): "
            "(1) Visibility of system status, (2) Match with real world, (3) User control/freedom, "
            "(4) Consistency and standards, (5) Error prevention, (6) Recognition over recall, "
            "(7) Flexibility and efficiency, (8) Aesthetic minimalism, "
            "(9) Help recognise/diagnose/recover from errors, (10) Help and documentation.\n"
            "WCAG 2.2 POUR principles: Perceivable, Operable, Understandable, Robust. "
            "Level AA minimum for legal compliance. Key AA requirements: "
            "4.5:1 colour contrast (normal text), 3:1 (large text), keyboard navigability, "
            "visible focus indicators, text alternatives for non-text content.\n"
            "UX research method selection: Qualitative (interviews, observation, diary studies) for 'why'; "
            "Quantitative (surveys, analytics, A/B tests) for 'how many'. n=5 for usability, n=40+ for surveys.\n"
            "IA rules: card sorting (open = discover categories, closed = test existing), "
            "tree testing (validate IA without visual design), every page reachable in ≤3 clicks."
        ),
        "domain_tags": ["design thinking", "UX research", "usability heuristics", "WCAG", "accessibility", "information architecture", "prototyping"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },

    # ── Emerging Standards & Frameworks (2024-2026) ───────────────────────────
    {
        "skill_id": "ai-governance-risk",
        "name": "AI Governance & Risk Management (NIST AI RMF / ISO 42001)",
        "category": "Specialized Services",
        "description": (
            "Comprehensive AI governance using NIST AI RMF 1.0 four functions (GOVERN/MAP/MEASURE/MANAGE), "
            "ISO 42001:2023 AI Management System (world's first AIMS standard, 38 controls), "
            "and EU AI Act 2025-2026 enforcement timeline. For organizations building or deploying AI systems."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "LEGAL-01", "SECURITY-01", "DATA-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the AI Governance & Risk Management skill installed.\n"
            "NIST AI RMF 1.0 four core functions:\n"
            "GOVERN — establish accountability, policies, culture, and risk tolerance for AI.\n"
            "MAP — identify and classify AI risks (technical, organizational, societal context).\n"
            "MEASURE — analyse, assess, benchmark, and monitor AI risks and impacts.\n"
            "MANAGE — prioritise and mitigate AI risks; plan for contingencies and residual risk.\n"
            "Apply all four functions in sequence for any AI system assessment.\n"
            "ISO 42001:2023 AIMS structure: Context (Clause 4) → Leadership (5) → Planning (6) → "
            "Support (7) → Operations (8) → Performance Evaluation (9) → Improvement (10). "
            "38 controls across 10 control categories including AI system impact assessment, "
            "data governance, AI objectives, and responsible AI practices. "
            "PDCA lifecycle: Plan (policy, objectives, risk) → Do (implement controls) → "
            "Check (audit, monitor) → Act (continual improvement). "
            "Certification pathway: stage 1 readiness audit → stage 2 certification → annual surveillance.\n"
            "EU AI Act enforcement timeline (CRITICAL — dates are mandatory):\n"
            "February 2, 2025: Prohibited AI practices now ACTIVE. Banned: social scoring by public "
            "authorities, real-time remote biometric surveillance in public spaces, subliminal "
            "manipulation, AI exploiting vulnerabilities of specific groups.\n"
            "August 2, 2025: GPAI (General Purpose AI) model rules + governance obligations active. "
            "GPAI providers must publish technical documentation, comply with copyright law, "
            "publish training data summaries.\n"
            "August 2, 2026: High-risk AI system requirements fully enforceable. "
            "High-risk categories: biometric identification, critical infrastructure, education, "
            "employment, essential services, law enforcement, migration control, justice.\n"
            "Fines: Prohibited AI = up to €35M or 7% of global annual turnover. "
            "High-risk non-compliance = up to €15M or 3%. GPAI = up to €15M or 3%.\n"
            "Conformity assessment for high-risk: technical documentation → risk management system → "
            "data governance → transparency → human oversight → accuracy/robustness testing → CE mark.\n"
            "Always label AI systems with their EU AI Act risk tier and applicable compliance deadline."
        ),
        "domain_tags": ["NIST AI RMF", "ISO 42001", "EU AI Act", "AI governance", "AI risk management", "AIMS", "GPAI"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "dora-operational-resilience",
        "name": "DORA Digital Operational Resilience (EU Regulation)",
        "category": "Specialized Services",
        "description": (
            "EU Digital Operational Resilience Act (DORA) compliance framework, effective January 17, 2025. "
            "Mandatory for financial entities across all EU member states: banks, insurers, investment firms, "
            "payment institutions, crypto-asset service providers, and critical ICT third-party providers."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "SECURITY-01", "LEGAL-01", "FINANCE-01"],
        "prompt_injection": (
            "You have the DORA Digital Operational Resilience skill installed.\n"
            "DORA is in full force as of January 17, 2025. Non-compliance exposes financial entities to "
            "fines up to 2% of total annual worldwide turnover (entities) or up to €5M (individuals).\n"
            "DORA 5 pillars — assess compliance against all 5:\n"
            "(1) ICT Risk Management: ICT risk framework, documented policies, business continuity plan, "
            "disaster recovery with RTO/RPO targets. Board-level accountability mandatory.\n"
            "(2) ICT-Related Incident Management & Reporting: classify incidents by severity. "
            "Major ICT incidents reported to competent authority: 4 hours (initial notification), "
            "72 hours (intermediate report), 1 month (final report). "
            "Operational disruption thresholds trigger mandatory reporting.\n"
            "(3) Digital Operational Resilience Testing (DORT): annual basic testing (vulnerability "
            "assessments, network/infrastructure scanning, source code reviews, scenario-based tests); "
            "Threat-Led Penetration Testing (TLPT) every 3 years for significant entities.\n"
            "(4) ICT Third-Party Risk Management: mandatory contractual requirements with ICT providers "
            "(exit strategy, audit rights, SLAs, data location, sub-contractor disclosure). "
            "Maintain ICT third-party register. Critical ICT providers face direct EU oversight.\n"
            "(5) Information Sharing: voluntary cyber threat intelligence sharing with other financial "
            "entities — share IoCs, TTPs, and threat actor information.\n"
            "DORA scope: credit institutions, payment institutions, e-money institutions, investment firms, "
            "crypto-asset service providers, insurance/reinsurance undertakings, pension funds, "
            "credit rating agencies, crowdfunding platforms, data reporting services.\n"
            "Always conclude: 'Engage a qualified DORA compliance specialist for implementation. "
            "National Competent Authority guidance supersedes general interpretation.'"
        ),
        "domain_tags": ["DORA", "digital operational resilience", "ICT risk", "third-party risk", "operational resilience", "EU financial regulation"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "nis2-eu-cybersecurity",
        "name": "NIS2 EU Cybersecurity Compliance Framework",
        "category": "Specialized Services",
        "description": (
            "NIS2 Directive (EU 2022/2555) compliance, active October 18, 2024. "
            "Covers 18 critical sectors, management accountability obligations, "
            "24-hour incident notification requirements, and fines up to €10M or 2% of global revenue."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "SECURITY-01", "LEGAL-01"],
        "prompt_injection": (
            "You have the NIS2 EU Cybersecurity Compliance skill installed.\n"
            "NIS2 has been in force since October 18, 2024. It supersedes NIS1 and significantly expands scope.\n"
            "NIS2 18 critical sectors — determine scope:\n"
            "Highly Critical (Annex I): Energy, Transport, Banking, Financial market infrastructures, "
            "Health, Drinking water, Wastewater, Digital infrastructure, ICT service management (B2B), "
            "Public administration, Space.\n"
            "Critical (Annex II): Postal/courier, Waste management, Chemicals, "
            "Food production/processing/distribution, Manufacturing (medical devices, computers, "
            "electrical equipment, machinery, motor vehicles), Digital providers, Research.\n"
            "Size thresholds: Essential Entity = large (>250 employees OR >€50M turnover) in Annex I. "
            "Important Entity = medium (>50 employees OR >€10M turnover) in Annex I or II.\n"
            "NIS2 security measures (Article 21 — 10 minimum requirements):\n"
            "(1) Risk analysis and information security policies, (2) Incident handling, "
            "(3) Business continuity and crisis management, (4) Supply chain security, "
            "(5) Network/information systems security, (6) Policies for assessing effectiveness, "
            "(7) Cybersecurity hygiene and training, (8) Cryptography and encryption, "
            "(9) HR security, access control, asset management, (10) MFA and secured communications.\n"
            "Incident reporting timeline: 24 hours — early warning to CSIRT/NCA; "
            "72 hours — incident notification with initial assessment; 1 month — final report.\n"
            "Management accountability: senior management personally liable for non-compliance. "
            "Management body must approve cybersecurity measures, receive training, and oversee implementation.\n"
            "Fines: Essential Entities = up to €10M or 2% global annual turnover (whichever higher). "
            "Important Entities = up to €7M or 1.4% global annual turnover.\n"
            "Supply chain: evaluate third-party supplier cybersecurity posture; "
            "include security clauses in all ICT contracts.\n"
            "Always conclude: 'Consult your national NCA (National Competent Authority) for jurisdiction-specific guidance.'"
        ),
        "domain_tags": ["NIS2", "EU cybersecurity", "incident reporting", "critical infrastructure", "supply chain security", "management accountability"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "cmmc-defense-contracting",
        "name": "CMMC 2.0 Defense Contracting Compliance",
        "category": "Specialized Services",
        "description": (
            "Cybersecurity Maturity Model Certification (CMMC) 2.0 compliance for US Department of Defense "
            "contractors. Phase 1 effective November 10, 2025. Covers all three CMMC levels, "
            "NIST SP 800-171 Rev 3 (110 controls), C3PAO assessment process, and POA&M management."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "SECURITY-01", "LEGAL-01"],
        "prompt_injection": (
            "You have the CMMC 2.0 Defense Contracting Compliance skill installed.\n"
            "CMMC 2.0 is effective November 10, 2025 (Phase 1). DoD contracts now include CMMC requirements.\n"
            "CMMC 2.0 three levels:\n"
            "Level 1 — Foundational (FCI — Federal Contract Information): "
            "17 practices from FAR 52.204-21; annual self-assessment by company senior official; "
            "applies to all DoD contractors handling FCI. No third-party assessment required.\n"
            "Level 2 — Advanced (CUI — Controlled Unclassified Information): "
            "110 practices aligned to NIST SP 800-171 Rev 3; "
            "Prioritised acquisitions: third-party C3PAO assessment every 3 years; "
            "Non-prioritised: annual self-assessment. "
            "POA&M items allowed (90-day remediation window for minor deficiencies).\n"
            "Level 3 — Expert (CUI+ / advanced persistent threats): "
            "Adds 24+ practices from NIST SP 800-172; "
            "Government-led assessment (DIBCAC — Defense Industrial Base Cybersecurity Assessment Center); "
            "Targets contractors supporting DoD's most critical programmes.\n"
            "NIST SP 800-171 Rev 3 — 17 control families (Level 2): "
            "Access Control (22), Awareness/Training (3), Audit/Accountability (9), "
            "Configuration Management (9), Identification/Authentication (11), Incident Response (3), "
            "Maintenance (6), Media Protection (9), Personnel Security (2), Physical Protection (6), "
            "Risk Assessment (3), Security Assessment (4), System/Comms Protection (16), "
            "System/Information Integrity (7), Planning (2), System/Services Acquisition (3), "
            "Supply Chain Risk Management (5). 110 controls total — all must be met for Level 2.\n"
            "SPRS score: 110 minus deductions per failed practice. Report via Supplier Performance Risk System.\n"
            "Assessment pathway: C3PAO selection → documentation review → assessment → "
            "CMMC-AB certification → upload to eMASS.\n"
            "POA&M rules: documented, time-bound (90 days max), mitigating controls required. "
            "Practices below minimum cannot be on POA&M at time of assessment.\n"
            "Always conclude: 'Engage a CMMC Registered Practitioner (RP) or Registered Practitioner Organization (RPO) for assessment preparation.'"
        ),
        "domain_tags": ["CMMC", "NIST 800-171", "DoD contracts", "CUI", "C3PAO", "defense contracting", "cybersecurity certification"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "signal-based-selling-revops",
        "name": "Signal-Based Selling & Revenue Operations (RevOps)",
        "category": "Sales & Business Dev",
        "description": (
            "Modern revenue growth playbook combining signal-based selling (real-time intent triggers) "
            "with Revenue Operations (RevOps) alignment. Delivers 47% better conversion rates, "
            "5x win rate for first-to-contact, and 19% faster revenue growth vs. siloed GTM teams."
        ),
        "author": "Directorate",
        "compatible_agents": ["HUNTER-01", "CLOSER-01", "ACCOUNT-01", "ANALYST-01", "RESEARCH-01"],
        "prompt_injection": (
            "You have the Signal-Based Selling & RevOps skill installed.\n"
            "SIGNAL-BASED SELLING:\n"
            "First-party signals (highest intent): pricing/product page visits, demo requests, "
            "trial sign-ups, high product engagement, upgrade-related support queries.\n"
            "Third-party signals (intent data): G2/Capterra category research, LinkedIn job postings "
            "(hiring for roles that use your solution = buying signal), funding announcements, "
            "tech stack additions (BuiltWith/Bombora), executive changes.\n"
            "Trigger event library — act within 24 hours:\n"
            "Funding announced: Company is spending, decision-makers are hired, budget exists.\n"
            "Key executive hire (CTO/CMO/COO): New leader = new mandate = new tools.\n"
            "Competitor review spike (G2/Capterra): Active evaluation in progress — first to engage wins.\n"
            "Job posting for role your tool replaces: Manual process = your automation opportunity.\n"
            "Earnings call mention of pain your product solves: Board-level pain = budget approved.\n"
            "First-to-contact (within 1 hour of trigger) achieves 5x win rate vs. 24-48h response.\n"
            "Conversion lift: signal-based outreach = 47% better conversion, 43% larger average deal size, "
            "38% more closed-won deals vs. untriggered cold outreach (2025 benchmarks).\n"
            "REVENUE OPERATIONS (RevOps):\n"
            "Four pillars: People (unified GTM team: SDR/AE/CS/Marketing ops), "
            "Process (documented playbooks with SLAs at every handoff), "
            "Data (single source of truth, clean CRM hygiene, defined tech stack ownership), "
            "Technology (integration architecture, no tool redundancy).\n"
            "North star metric: ONE shared metric across Marketing + Sales + CS "
            "(e.g., Net Revenue Retention, Pipeline Velocity, or Qualified Pipeline Created).\n"
            "Pipeline velocity formula: (# Qualified Opportunities × Avg Deal Size × Win Rate) ÷ Sales Cycle Length.\n"
            "Lead scoring: Fit score (ICP firmographic match, 0-100) + Engagement score (behaviour/intent, 0-100). "
            "MQL threshold: Fit ≥ 60 + Engagement ≥ 40. SQL = AE-qualified from MQL after discovery.\n"
            "RevOps tech stack: CRM (source of truth) → Marketing Automation → Sales Engagement → "
            "Revenue Intelligence → BI/reporting. Ensure bidirectional sync between all layers."
        ),
        "domain_tags": ["signal-based selling", "RevOps", "intent data", "pipeline velocity", "lead scoring", "revenue operations", "GTM alignment"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },
    {
        "skill_id": "geo-ai-search-optimization",
        "name": "Generative Engine Optimization (GEO) & AI Search",
        "category": "Marketing & Creative",
        "description": (
            "Next-generation search optimization for AI-powered engines: Google AI Overviews, "
            "ChatGPT Search, Perplexity, and Bing Copilot. 58% of users use AI tools for product "
            "discovery (2025) and AI-driven retail traffic is up 4,700% YoY. Master GEO alongside E-E-A-T."
        ),
        "author": "Directorate",
        "compatible_agents": ["SEO-01", "Author-01", "BRAND-01", "RESEARCH-01", "SOCIAL-01"],
        "prompt_injection": (
            "You have the Generative Engine Optimization (GEO) skill installed.\n"
            "GEO vs SEO: Traditional SEO targets Google's algorithmic ranking. "
            "GEO targets AI-generated answers — content AI engines cite as authoritative and present "
            "in zero-click responses. Both disciplines are now required simultaneously.\n"
            "2025 context: 58% of users use AI tools for product discovery. "
            "AI-driven retail traffic up 4,700% YoY. ChatGPT Search, Perplexity, and Google AI Overviews "
            "are primary discovery channels for complex queries.\n"
            "GEO optimization principles:\n"
            "(1) Authority & Credibility signals: AI engines prioritise cited, referenced, linked content. "
            "Build: peer citations, expert bylines, original research/data, 'as cited in' mentions from authoritative sources.\n"
            "(2) Earned media bias: AI search favours content independently discussed, quoted, or referenced. "
            "PR strategy directly boosts GEO — get cited in industry publications.\n"
            "(3) Structured, quotable content: AI engines excerpt specific paragraphs. "
            "Write in short, complete, factual paragraphs that stand alone as answers. "
            "Include: definitions, stats with sources, step-by-step lists, comparison tables.\n"
            "(4) Semantic entity optimization: build topical authority clusters, not just keyword pages. "
            "Cover the full topic graph (main concept + related entities + supporting concepts).\n"
            "(5) Source trustworthiness: Domain Authority supplemented by entity mentions in knowledge "
            "graphs (Wikipedia, Wikidata), structured data (schema.org), author E-E-A-T signals.\n"
            "(6) Platform-specific GEO:\n"
            "Google AI Overviews: optimise Featured Snippet-style answers (question → direct answer → context), "
            "use FAQ schema, target Position 0.\n"
            "ChatGPT Search (powered by Bing): ensure robots.txt allows Bingbot, "
            "submit sitemap to Bing Webmaster Tools, use news-style recency signals.\n"
            "Perplexity: fresh, dated content with clear publication dates performs better. "
            "Real-time indexed sources favoured.\n"
            "Measurement: track AI Overview appearances (Search Console), brand mention monitoring in "
            "AI responses (manual testing + tools), dark social traffic growth (AI referrals).\n"
            "E-E-A-T 2025: Experience is weighted equally with Expertise. "
            "Demonstrate first-hand experience: original data, case studies, real examples, product testing. "
            "AI-generated content without demonstrable experience signals low E-E-A-T."
        ),
        "domain_tags": ["GEO", "AI search", "Google AI Overviews", "Perplexity", "ChatGPT Search", "E-E-A-T", "generative engine optimization"],
        "tool_actions": [],
        "price_cents": 99900,
        "status": "active",
    },
    {
        "skill_id": "ai-agent-engineering",
        "name": "AI Agent Engineering & Agentic Design Patterns",
        "category": "Technical & IT",
        "description": (
            "Production-grade AI agent engineering: ReAct, prompt chaining, orchestrator-workers, and "
            "multi-agent swarm patterns. Tool use, RAG integration, memory architectures, and safety controls. "
            "Based on Anthropic's Building Effective Agents guidance and 2025 agentic AI standards."
        ),
        "author": "Directorate",
        "compatible_agents": ["CODE-01", "DATA-01", "DEVOPS-01", "RESEARCH-01", "API-01"],
        "prompt_injection": (
            "You have the AI Agent Engineering & Agentic Design Patterns skill installed.\n"
            "CORE AGENTIC PATTERNS (apply the right pattern per task):\n"
            "(1) Prompt Chaining: sequential LLM calls where output feeds next. "
            "Best for: deterministic multi-step workflows, validation gates, clear subtask boundaries.\n"
            "(2) Routing: classify input, direct to specialised downstream agent/prompt. "
            "Best for: diverse input types, parallel specialist agents, customer triage.\n"
            "(3) Parallelisation: simultaneous LLM calls, aggregate results. "
            "Best for: independent subtasks, sectioning long documents, majority-vote verification.\n"
            "(4) Orchestrator-Workers: orchestrator plans, delegates to specialised workers. "
            "Best for: complex tasks requiring different tools/skills, multi-domain problems.\n"
            "(5) Evaluator-Optimiser: one LLM generates, another evaluates — feedback loop. "
            "Best for: quality-sensitive outputs, iterative refinement, automated quality assurance.\n"
            "(6) ReAct (Reason + Act): interleave Thought → Tool Call → Observation. "
            "Best for: tool-using agents, search-augmented reasoning, dynamic problem solving.\n"
            "TOOL USE BEST PRACTICES:\n"
            "Each tool: clear name, complete description, precise parameter schema. "
            "Ambiguous tool definitions cause agent errors. Each tool does ONE thing well.\n"
            "Error handling: retry with exponential backoff (max 3 attempts), "
            "surface tool errors to agent for replanning, set timeouts on all external calls.\n"
            "RAG INTEGRATION:\n"
            "Chunking: semantic chunking > fixed-size for coherence. "
            "256-512 tokens for retrieval precision, parent-child chunks for context.\n"
            "Retrieval: hybrid search (dense vectors + sparse BM25) outperforms vector-only. "
            "Reranking with cross-encoder improves precision. Self-query for metadata filtering.\n"
            "MEMORY ARCHITECTURES:\n"
            "In-context (short-term): conversation history, current task state.\n"
            "External (long-term): vector store (semantic similarity), "
            "key-value store (entity/preference lookups), SQL (structured history).\n"
            "Summarise + store key insights; never carry full transcripts indefinitely.\n"
            "MULTI-AGENT SAFETY:\n"
            "Trust hierarchy: orchestrating agent has elevated permissions; "
            "sub-agents scoped to minimum required tools and data.\n"
            "Communication: structured JSON handoff between agents (not free-text) reduces hallucination.\n"
            "Human-in-the-loop checkpoints: require approval before irreversible actions "
            "(sending emails, writing to production, making purchases, deleting data).\n"
            "Prefer reversible actions; minimise blast radius; "
            "pause-and-verify for ambiguous or high-stakes steps.\n"
            "EVALUATION: test with adversarial inputs, edge cases, tool failure scenarios. "
            "Measure: task completion rate, tool call accuracy, hallucination rate, latency, cost per task."
        ),
        "domain_tags": ["AI agents", "ReAct", "agentic AI", "multi-agent systems", "RAG", "tool use", "LLM orchestration"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "soc2-compliance",
        "name": "SOC 2 Type II Compliance Framework (2025 Edition)",
        "category": "Specialized Services",
        "description": (
            "AICPA SOC 2 compliance with 2025 updated guidance covering all 5 Trust Services Criteria, "
            "Type I vs Type II distinctions, evidence collection playbooks, AI-specific scoping, "
            "and auditor selection. Essential for SaaS and tech companies serving enterprise customers."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "SECURITY-01", "LEGAL-01", "DEVOPS-01"],
        "prompt_injection": (
            "You have the SOC 2 Type II Compliance Framework (2025 Edition) skill installed.\n"
            "SOC 2 is an AICPA-defined attestation standard. A qualified CPA firm must issue the report.\n"
            "TYPE I vs TYPE II:\n"
            "Type I: point-in-time — are controls designed appropriately? Single date, 3-6 months to achieve.\n"
            "Type II: operating effectiveness over minimum 6 months (typically 12). "
            "Enterprise procurement requires Type II. Timeline: 6-month audit period + 2-3 month review = 9-15 months.\n"
            "5 TRUST SERVICES CRITERIA (TSC):\n"
            "(CC) Security (MANDATORY): logical and physical access controls, change management, "
            "risk management, monitoring, incident response. Maps to COSO framework.\n"
            "(A) Availability: system availability commitments, performance monitoring, DR, redundancy.\n"
            "(PI) Processing Integrity: complete, accurate, timely processing; "
            "data validation, error handling, output reconciliation.\n"
            "(C) Confidentiality: classification policy, AES-256/TLS 1.3 encryption, "
            "least-privilege access to confidential data, disposal.\n"
            "(P) Privacy: AICPA Privacy Management Framework — notice, consent, collection, use, "
            "retention, disposal. Aligned with GDPR and CCPA. Requires DPAs and privacy notices.\n"
            "SCOPE DEFINITION (critical first step): define systems, infrastructure, data, people, processes. "
            "Include critical dependencies (cloud providers, subprocessors). Narrow scope = lower cost.\n"
            "AI system scoping (2025 AICPA guidance): if AI/ML models make decisions affecting service "
            "commitments, include model training, validation, and monitoring in scope.\n"
            "EVIDENCE COLLECTION by category:\n"
            "Access Control: quarterly user access reviews, MFA logs, offboarding records, "
            "privileged access logs, least-privilege reviews.\n"
            "Change Management: change tickets with approvals, deployment logs, rollback evidence.\n"
            "Risk Assessment: annual risk assessment docs, vendor risk reviews.\n"
            "Incident Response: IR policy, documented incidents (even minor), response timelines.\n"
            "Vendor Management: vendor inventory, security questionnaires, BAAs/DPAs, re-assessment cadence.\n"
            "Monitoring: SIEM alerts, vulnerability scan results, penetration test + remediation evidence.\n"
            "COMMON AUDIT FAILURES: missing evidence for control periods, "
            "terminated employee access not revoked promptly, no documented access reviews, "
            "change management bypassed for emergency fixes without post-approval.\n"
            "Always conclude: 'SOC 2 attestation must be issued by a licensed CPA firm. "
            "Engage a qualified auditor and legal counsel.'"
        ),
        "domain_tags": ["SOC 2", "Trust Services Criteria", "Type II", "AICPA", "audit evidence", "security compliance", "SaaS compliance"],
        "tool_actions": [],
        "price_cents": 199900,
        "status": "active",
    },
    {
        "skill_id": "ifrs-s1-s2-climate",
        "name": "IFRS S1/S2 Sustainability & Climate Disclosure",
        "category": "Specialized Services",
        "description": (
            "IFRS Sustainability Disclosure Standards: S1 (General Requirements, effective Jan 1, 2024) "
            "and S2 (Climate-related Disclosures, effective Jan 1, 2024). Includes December 2025 GHG "
            "protocol amendments, TCFD integration, and global adoption landscape by jurisdiction."
        ),
        "author": "Directorate",
        "compatible_agents": ["COMPLIANCE-01", "FINANCE-01", "RESEARCH-01", "PR-01"],
        "prompt_injection": (
            "You have the IFRS S1/S2 Sustainability & Climate Disclosure skill installed.\n"
            "IFRS S1 — General Requirements for Disclosure of Sustainability-related Financial Information:\n"
            "Effective date: January 1, 2024 (mandatory for ISSB-required jurisdictions).\n"
            "Purpose: disclose sustainability-related risks and opportunities that could reasonably be "
            "expected to affect the entity's cash flows, access to finance, or cost of capital.\n"
            "Core content (4 pillars — identical to TCFD): "
            "Governance (board oversight, management accountability), "
            "Strategy (sustainability risks/opportunities, resilience analysis), "
            "Risk Management (identification, assessment, monitoring), "
            "Metrics and Targets (quantitative KPIs, progress toward targets).\n"
            "Materiality: IFRS S1 uses single materiality (investor-focused financial materiality only), "
            "unlike EU CSRD which uses double materiality.\n"
            "IFRS S2 — Climate-related Disclosures:\n"
            "Effective date: January 1, 2024.\n"
            "Physical risks: acute (extreme weather events) and chronic (long-term climate shifts).\n"
            "Transition risks: policy/regulatory, technology, market, reputational.\n"
            "Climate scenario analysis: assess resilience under at least 2 scenarios including 1.5°C pathway.\n"
            "Scope 3 GHG: disclose all 15 Scope 3 categories if material; explain if not disclosed.\n"
            "DECEMBER 2025 GHG AMENDMENTS:\n"
            "ISSB issued targeted amendments to IFRS S2 in December 2025: "
            "clarifies measurement of Scope 3 Category 15 (financed emissions for financial institutions), "
            "provides additional guidance on GHG intensity metrics, and simplifies "
            "cross-industry metric disclosures for smaller reporters. "
            "Core Scope 1/2/3 GHG Protocol framework is unchanged.\n"
            "GLOBAL ADOPTION (2025): Australia (mandatory from July 2024 start), "
            "UK (ISSB-aligned for large companies), Singapore (phased 2025-2027), "
            "Japan (phased 2025-2027), Canada (consultation phase). "
            "EU: CSRD/ESRS is separate but ISSB-EFRAG interoperability guidance published.\n"
            "TCFD integration: IFRS S2 fully incorporates TCFD. Gap to IFRS S2 from TCFD: "
            "add formal scenario analysis and Scope 3 completeness.\n"
            "Assurance: IAASB ISSA 5000 applies. Start with limited assurance; target reasonable by 2027.\n"
            "Always note: 'IFRS S1/S2 requirements vary by jurisdiction. "
            "Confirm applicable standards with legal and audit advisers.'"
        ),
        "domain_tags": ["IFRS S1", "IFRS S2", "ISSB", "climate disclosure", "TCFD", "Scope 3", "sustainability reporting", "GHG"],
        "tool_actions": [],
        "price_cents": 149900,
        "status": "active",
    },

    # ── Learning & Development ─────────────────────────────────────────────────
    {
        "skill_id": "learning-development-addie",
        "name": "Learning & Development (ADDIE/Bloom's)",
        "category": "Learning & Development",
        "description": (
            "Instructional design mastery: ADDIE model, Bloom's Taxonomy (revised), "
            "Kirkpatrick's 4-level evaluation model, 70-20-10 learning framework, "
            "and microlearning design. For building courses, workshops, and blended learning programmes."
        ),
        "author": "Directorate",
        "compatible_agents": ["TRAINER-01", "COACH-01", "HR-01", "Author-01"],
        "prompt_injection": (
            "You have the Learning & Development (ADDIE/Bloom's) skill installed.\n"
            "ADDIE model: "
            "(1) Analysis: Training needs analysis (TNA) — performance gap (current vs. desired state), "
            "root cause (knowledge/skill/attitude/environment), target audience profile. "
            "(2) Design: Write learning objectives (Bloom's verb + specific knowledge/skill), "
            "sequence content (simple → complex, known → unknown), select delivery method. "
            "(3) Development: Storyboard first; 3-2-1 rule (max 3 key points, 2 practice activities, 1 summary/assessment per module). "
            "(4) Implementation: Pilot with 5 representative learners, gather feedback, train facilitators. "
            "(5) Evaluation: Apply Kirkpatrick's model.\n"
            "Bloom's Taxonomy (revised, 6 levels with action verbs): "
            "Remember (define/list/recall), Understand (explain/summarise/classify), "
            "Apply (use/implement/demonstrate), Analyse (differentiate/compare/deconstruct), "
            "Evaluate (judge/critique/justify), Create (design/construct/produce). "
            "Learning objective format: 'By the end of this [module], learners will be able to [Bloom's verb] [specific skill]'.\n"
            "Kirkpatrick 4-level evaluation: "
            "L1 Reaction (satisfaction survey, target eNPS >7/10), "
            "L2 Learning (pre/post assessment, target >80% pass + >15% score improvement), "
            "L3 Behaviour (on-the-job application at 30/60/90 days — manager observation checklist), "
            "L4 Results (business impact metric tied to original TNA gap). Measure all 4 levels.\n"
            "70-20-10 model: 70% challenging on-the-job experiences (stretch assignments, action learning), "
            "20% developmental relationships (mentoring, coaching, peer learning), "
            "10% formal training (courses, workshops). Design programmes with all three.\n"
            "Microlearning: max 5 min/module, single learning objective, "
            "spaced repetition at 1 day/1 week/1 month post-learning, mobile-first format."
        ),
        "domain_tags": ["ADDIE", "Bloom's Taxonomy", "Kirkpatrick", "instructional design", "70-20-10", "learning objectives", "microlearning"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
    {
        "skill_id": "skills-based-hr",
        "name": "Skills-Based Hiring & Workforce Planning (2025)",
        "category": "Learning & Development",
        "description": (
            "Modern HR transformation: replace credential-based hiring with skills-based hiring and "
            "workforce planning. 81% of organizations using skills-based hiring reduce time-to-hire. "
            "Built on SHRM 2024 competency model, skills taxonomy design, internal talent marketplace, "
            "and pay transparency frameworks aligned to 2025 legislation."
        ),
        "author": "Directorate",
        "compatible_agents": ["HR-01", "RECRUITER-01", "TRAINER-01", "COACH-01", "ANALYST-01"],
        "prompt_injection": (
            "You have the Skills-Based Hiring & Workforce Planning (2025) skill installed.\n"
            "SKILLS-BASED HIRING:\n"
            "Core principle: evaluate candidates on demonstrated skills and competencies, not proxy credentials "
            "(degrees, job titles, years of experience). Evidence: 81% of companies using skills-based "
            "hiring report reduced time-to-hire; 75% of HR professionals see it as the future of work (SHRM 2024).\n"
            "Skills taxonomy — three tiers:\n"
            "Tier 1: Core technical skills (role-specific, measurable, testable by work sample or assessment).\n"
            "Tier 2: Transferable skills (analytical thinking, communication, project management, data literacy).\n"
            "Tier 3: Human skills (empathy, creativity, complex problem-solving, ethical judgment — "
            "increasingly critical as AI automates Tier 1 and 2 tasks).\n"
            "SHRM 2024 Competency Model 9 competencies: Ethical Practice, Leadership & Navigation, "
            "Business Acumen, Consultation, Critical Evaluation, Cultural Effectiveness, "
            "Relationship Management, Communication, Global & Cultural Effectiveness.\n"
            "Job architecture transformation:\n"
            "Step 1: Audit job descriptions — remove unnecessary degree requirements, "
            "replace generic requirements with specific skill statements.\n"
            "Step 2: Create skills profiles per role — ranked by criticality (must-have/preferred/trainable).\n"
            "Step 3: Build assessment tools — structured work samples, skills tests, portfolio review, "
            "structured behavioural interviews (STAR mapped to specific demonstrated skill).\n"
            "Step 4: Train hiring managers on skills assessment; calibrate; reduce affinity bias.\n"
            "INTERNAL TALENT MARKETPLACE:\n"
            "Skill inventory: map current workforce skills via self-assessment + manager validation.\n"
            "Skill gap analysis: current vs. future-state skills needed (2-3 year horizon).\n"
            "Internal mobility: post internal roles before external hire; "
            "companies with strong internal mobility retain staff 2x longer.\n"
            "Gig/project marketplace: short-term internal projects to develop skills and signal talent.\n"
            "PAY TRANSPARENCY (2025 legislation):\n"
            "USA mandatory ranges: Colorado, California, New York, Washington, Illinois. "
            "Best practice: skills-based pay bands (same title, same band, pay varies by skill proficiency).\n"
            "AI augmentation: use AI to map skills to roles, identify adjacent skills for reskilling paths, "
            "but maintain human judgment for all hiring decisions. "
            "Test any AI screening tool for adverse impact before deployment.\n"
            "Workforce metrics: skills coverage ratio, internal mobility rate, "
            "time-to-productivity for new hires, skills gap closure rate, learning ROI."
        ),
        "domain_tags": ["skills-based hiring", "workforce planning", "skills taxonomy", "SHRM", "internal talent marketplace", "pay transparency", "HR transformation"],
        "tool_actions": [],
        "price_cents": 79900,
        "status": "active",
    },
]


def main() -> None:
    ensure_schema(engine)

    upsert_sql = """
        insert into skill_catalog
          (skill_id, name, category, description, author, compatible_agents,
           prompt_injection, domain_tags, tool_actions, price_cents, status)
        values
          (:skill_id, :name, :category, :description, :author,
           cast(:compatible_agents as jsonb), :prompt_injection,
           cast(:domain_tags as jsonb), cast(:tool_actions as jsonb),
           :price_cents, :status)
        on conflict (skill_id) do update set
          name = excluded.name,
          category = excluded.category,
          description = excluded.description,
          author = excluded.author,
          compatible_agents = excluded.compatible_agents,
          prompt_injection = excluded.prompt_injection,
          domain_tags = excluded.domain_tags,
          tool_actions = excluded.tool_actions,
          price_cents = excluded.price_cents,
          status = excluded.status;
    """

    with engine.begin() as conn:
        for skill in SKILLS:
            conn.execute(
                text(upsert_sql),
                {
                    **skill,
                    "compatible_agents": json.dumps(skill["compatible_agents"]),
                    "domain_tags": json.dumps(skill["domain_tags"]),
                    "tool_actions": json.dumps(skill["tool_actions"]),
                },
            )

    print(f"Seeded {len(SKILLS)} skills into skill_catalog.")


if __name__ == "__main__":
    main()
