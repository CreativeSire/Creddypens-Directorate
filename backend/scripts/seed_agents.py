from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import bindparam, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import engine
from app.schema import ensure_schema


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "agent_dossiers.json"

DEPARTMENT_MAP = {
    "CUSTOMER EXPERIENCE": "Customer Experience",
    "SALES & BUSINESS DEVELOPMENT": "Sales & Business Development",
    "MARKETING & CREATIVE": "Marketing & Creative",
    "OPERATIONS & ADMIN": "Operations & Admin",
    "TECHNICAL & IT": "Technical & IT",
    "SPECIALIZED SERVICES": "Specialized Services",
}

LEGACY_CODE_MAP = {
    "AUTHOR-01": "Author-01",
    "ASSISTANT-01": "Assistant-01",
    "ASSIST-01": "Assistant-01",
    "GREETER-01": "Greeter-01",
}


def canonical_code(code: str) -> str:
    raw = (code or "").strip()
    if not raw:
        return raw
    upper = raw.upper()
    if upper in LEGACY_CODE_MAP:
        return LEGACY_CODE_MAP[upper]
    if "-" not in raw:
        return upper
    prefix, suffix = raw.rsplit("-", 1)
    return f"{prefix.upper()}-{suffix}"


# ---------------------------------------------------------------------------
# Domain data: curated per-agent specialisation + colleague referrals.
# Keys must match the canonical code produced by canonical_code().
# related_agents → list of dicts with code, name, specialty.
# ---------------------------------------------------------------------------
AGENT_DOMAIN_DATA: dict[str, dict] = {
    "Greeter-01": {
        "domain_tags": ["visitor intake", "FAQ handling", "appointment scheduling", "lead routing", "inbound inquiry management"],
        "related_agents": [
            {"code": "SUPPORT-01", "name": "Technical Support Specialist", "specialty": "technical issues and product troubleshooting"},
            {"code": "QUALIFIER-01", "name": "Inbound Lead Qualification Specialist", "specialty": "qualifying and scoring inbound sales leads"},
            {"code": "SCHEDULE-01", "name": "Scheduling & Calendar Coordination Specialist", "specialty": "calendar management and meeting booking"},
        ],
        "out_of_scope_examples": ["technical debugging", "contract review", "sales negotiation", "content writing"],
    },
    "SUPPORT-01": {
        "domain_tags": ["technical support", "customer support tickets", "bug reporting", "product troubleshooting", "service issues"],
        "related_agents": [
            {"code": "COMPLAINT-01", "name": "Complaint Resolution Specialist", "specialty": "escalations and service recovery"},
            {"code": "CODE-01", "name": "Software Development & Code Review Specialist", "specialty": "software bugs and code-level issues"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "infrastructure and deployment issues"},
        ],
        "out_of_scope_examples": ["sales prospecting", "content creation", "HR management", "legal review"],
    },
    "RETENTION-01": {
        "domain_tags": ["customer success", "churn prevention", "renewal management", "upselling", "customer health monitoring", "account expansion"],
        "related_agents": [
            {"code": "ACCOUNT-01", "name": "Account Executive & Relationship Manager", "specialty": "account management and strategic relationships"},
            {"code": "FEEDBACK-01", "name": "Customer Feedback & Survey Specialist", "specialty": "collecting and analysing customer feedback"},
            {"code": "SUPPORT-01", "name": "Technical Support Specialist", "specialty": "technical issues blocking customer success"},
        ],
        "out_of_scope_examples": ["new lead generation", "technical debugging", "content creation", "legal contracts"],
    },
    "COMPLAINT-01": {
        "domain_tags": ["complaint handling", "service recovery", "customer escalations", "dispute resolution", "refund management", "apology frameworks"],
        "related_agents": [
            {"code": "SUPPORT-01", "name": "Technical Support Specialist", "specialty": "technical root causes behind complaints"},
            {"code": "RETENTION-01", "name": "Customer Success & Retention Specialist", "specialty": "saving the relationship after a complaint"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "legal obligations in dispute resolution"},
        ],
        "out_of_scope_examples": ["sales outreach", "technical development", "HR policy", "content writing"],
    },
    "FEEDBACK-01": {
        "domain_tags": ["customer surveys", "feedback collection", "NPS", "CSAT", "sentiment analysis", "customer voice programs"],
        "related_agents": [
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "turning feedback data into actionable insights"},
            {"code": "RETENTION-01", "name": "Customer Success & Retention Specialist", "specialty": "acting on feedback to improve retention"},
            {"code": "RESEARCH-01", "name": "Business Research & Intelligence Analyst", "specialty": "broader market and competitive research"},
        ],
        "out_of_scope_examples": ["sales prospecting", "technical support", "content creation", "HR management"],
    },
    "ONBOARD-01": {
        "domain_tags": ["customer onboarding", "product setup guidance", "adoption acceleration", "success milestones", "onboarding journeys"],
        "related_agents": [
            {"code": "SUPPORT-01", "name": "Technical Support Specialist", "specialty": "technical blockers during onboarding"},
            {"code": "TRAINER-01", "name": "Training & Enablement Specialist", "specialty": "structured training programs and learning content"},
            {"code": "RETENTION-01", "name": "Customer Success & Retention Specialist", "specialty": "post-onboarding customer success"},
        ],
        "out_of_scope_examples": ["employee onboarding", "sales closing", "legal contracts", "content writing"],
    },
    "HUNTER-01": {
        "domain_tags": ["outbound prospecting", "cold outreach", "lead generation", "pipeline building", "sales development", "cold calling scripts", "LinkedIn outreach"],
        "related_agents": [
            {"code": "QUALIFIER-01", "name": "Inbound Lead Qualification Specialist", "specialty": "qualifying leads before they enter the pipeline"},
            {"code": "CLOSER-01", "name": "Sales Closer & Negotiation Specialist", "specialty": "closing deals once leads are qualified"},
            {"code": "EMAIL-01", "name": "Email Marketing Specialist", "specialty": "email sequences and outreach campaigns"},
        ],
        "out_of_scope_examples": ["content writing", "technical support", "HR processes", "legal review"],
    },
    "QUALIFIER-01": {
        "domain_tags": ["inbound lead qualification", "discovery calls", "BANT qualification", "pipeline management", "lead scoring", "ICP matching"],
        "related_agents": [
            {"code": "HUNTER-01", "name": "Outbound Sales Development Representative", "specialty": "generating new outbound leads"},
            {"code": "CLOSER-01", "name": "Sales Closer & Negotiation Specialist", "specialty": "closing qualified opportunities"},
            {"code": "DEMO-01", "name": "Product Demo & Presentation Specialist", "specialty": "product demonstrations for qualified prospects"},
        ],
        "out_of_scope_examples": ["content creation", "technical support", "HR policy", "legal review"],
    },
    "CLOSER-01": {
        "domain_tags": ["sales closing", "negotiation", "objection handling", "contract negotiation", "deal structuring", "pricing conversations"],
        "related_agents": [
            {"code": "PROPOSAL-01", "name": "Proposal & Quote Generation Specialist", "specialty": "building winning proposals and quotes"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "contract terms and legal review"},
            {"code": "ACCOUNT-01", "name": "Account Executive & Relationship Manager", "specialty": "post-close account management"},
        ],
        "out_of_scope_examples": ["content writing", "technical support", "HR management", "marketing strategy"],
    },
    "PARTNER-01": {
        "domain_tags": ["channel partnerships", "reseller programs", "strategic alliances", "partner enablement", "joint go-to-market", "partner recruitment"],
        "related_agents": [
            {"code": "ACCOUNT-01", "name": "Account Executive & Relationship Manager", "specialty": "managing ongoing partner accounts"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "partnership agreements and legal terms"},
            {"code": "PROPOSAL-01", "name": "Proposal & Quote Generation Specialist", "specialty": "partner proposals and co-sell documents"},
        ],
        "out_of_scope_examples": ["direct sales", "technical development", "content creation", "HR management"],
    },
    "ACCOUNT-01": {
        "domain_tags": ["account management", "client relationships", "upselling", "QBRs", "customer retention", "strategic account planning"],
        "related_agents": [
            {"code": "RETENTION-01", "name": "Customer Success & Retention Specialist", "specialty": "retention programs and churn prevention"},
            {"code": "PROPOSAL-01", "name": "Proposal & Quote Generation Specialist", "specialty": "renewal and expansion proposals"},
            {"code": "CLOSER-01", "name": "Sales Closer & Negotiation Specialist", "specialty": "re-negotiation and expansion deal closing"},
        ],
        "out_of_scope_examples": ["new prospect outreach", "technical support", "content creation", "HR management"],
    },
    "DEMO-01": {
        "domain_tags": ["product demonstrations", "sales presentations", "feature showcasing", "technical overview for prospects", "demo scripting"],
        "related_agents": [
            {"code": "QUALIFIER-01", "name": "Inbound Lead Qualification Specialist", "specialty": "qualifying prospects before demos"},
            {"code": "PROPOSAL-01", "name": "Proposal & Quote Generation Specialist", "specialty": "follow-up proposals after demos"},
            {"code": "VIDEO-01", "name": "Video Script Writer & Storyboard Specialist", "specialty": "video demo scripts and recorded walkthroughs"},
        ],
        "out_of_scope_examples": ["cold outreach", "content writing", "HR management", "technical debugging"],
    },
    "PROPOSAL-01": {
        "domain_tags": ["proposal writing", "quoting", "RFP responses", "pricing strategies", "business cases", "Statement of Work"],
        "related_agents": [
            {"code": "CLOSER-01", "name": "Sales Closer & Negotiation Specialist", "specialty": "negotiating and closing the proposal"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "legal terms within proposals and contracts"},
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "persuasive narrative and writing quality"},
        ],
        "out_of_scope_examples": ["cold outreach", "technical support", "HR policy", "social media"],
    },
    "Author-01": {
        "domain_tags": ["blog posts", "marketing copy", "email sequences", "ad copy", "video sales letters", "YouTube scripts", "brand storytelling", "long-form content"],
        "related_agents": [
            {"code": "SOCIAL-01", "name": "Social Media Manager", "specialty": "adapting content for social media channels"},
            {"code": "SEO-01", "name": "SEO Specialist & Content Optimizer", "specialty": "optimizing content for search rankings"},
            {"code": "EMAIL-01", "name": "Email Marketing Specialist", "specialty": "email campaign strategy and sequencing"},
        ],
        "out_of_scope_examples": ["sales prospecting", "technical support", "HR management", "legal review", "bookkeeping"],
    },
    "SOCIAL-01": {
        "domain_tags": ["social media content", "platform strategy", "community management", "social media campaigns", "content calendars", "engagement tactics"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "long-form content and copy that feeds social"},
            {"code": "BRAND-01", "name": "Brand Voice & Messaging Specialist", "specialty": "ensuring brand consistency across social"},
            {"code": "DESIGNER-01", "name": "Graphic Design & Visual Content Specialist", "specialty": "visual assets and graphics for posts"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "EMAIL-01": {
        "domain_tags": ["email campaigns", "drip sequences", "email automation", "newsletter writing", "A/B testing", "list segmentation", "deliverability"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "long-form copy and email narrative"},
            {"code": "HUNTER-01", "name": "Outbound Sales Development Representative", "specialty": "cold outreach and prospecting sequences"},
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "email performance analysis and reporting"},
        ],
        "out_of_scope_examples": ["social media management", "technical support", "HR management", "legal review"],
    },
    "VIDEO-01": {
        "domain_tags": ["video scripts", "storyboarding", "explainer videos", "video marketing", "YouTube content", "video sales letters", "tutorial scripts"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "written content that feeds into video"},
            {"code": "BRAND-01", "name": "Brand Voice & Messaging Specialist", "specialty": "keeping video messaging on-brand"},
            {"code": "DESIGNER-01", "name": "Graphic Design & Visual Content Specialist", "specialty": "visual style guides and storyboard art"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "SEO-01": {
        "domain_tags": ["SEO optimization", "keyword research", "on-page SEO", "content strategy for search", "backlink strategy", "technical SEO audits", "search rankings"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "writing SEO-optimized content"},
            {"code": "RESEARCH-01", "name": "Business Research & Intelligence Analyst", "specialty": "market and competitor research to inform SEO"},
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "SEO performance analytics and dashboards"},
        ],
        "out_of_scope_examples": ["social media management", "technical support", "HR management", "sales closing"],
    },
    "BRAND-01": {
        "domain_tags": ["brand voice", "messaging frameworks", "brand guidelines", "positioning statements", "tone of voice", "brand architecture"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "applying brand voice in written content"},
            {"code": "DESIGNER-01", "name": "Graphic Design & Visual Content Specialist", "specialty": "visual identity and brand assets"},
            {"code": "MEDIA-01", "name": "Public Relations & Media Relations Specialist", "specialty": "brand reputation and media positioning"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "Assistant-01": {
        "domain_tags": ["email management", "task organisation", "research summarisation", "meeting scheduling", "general administrative support", "document preparation"],
        "related_agents": [
            {"code": "SCHEDULE-01", "name": "Scheduling & Calendar Coordination Specialist", "specialty": "complex calendar and meeting logistics"},
            {"code": "PROJECT-01", "name": "Project Management & Coordination Specialist", "specialty": "multi-stakeholder project coordination"},
            {"code": "RESEARCH-01", "name": "Business Research & Intelligence Analyst", "specialty": "in-depth research and intelligence reports"},
        ],
        "out_of_scope_examples": ["technical development", "legal advice", "sales prospecting", "bookkeeping"],
    },
    "DATA-01": {
        "domain_tags": ["data entry", "database management", "data cleaning", "CRM data updates", "spreadsheet management", "data quality"],
        "related_agents": [
            {"code": "DATA-02", "name": "Data Engineering & Pipeline Specialist", "specialty": "automated data pipelines and ETL processes"},
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "analysing and visualising the data once it is clean"},
            {"code": "Assistant-01", "name": "Executive Virtual Assistant", "specialty": "broader administrative and operational support"},
        ],
        "out_of_scope_examples": ["technical development", "HR management", "sales closing", "content writing"],
    },
    "HR-01": {
        "domain_tags": ["HR policies", "employee relations", "performance management", "benefits administration", "people operations", "workforce planning", "employee handbook"],
        "related_agents": [
            {"code": "RECRUITER-01", "name": "Recruitment & Talent Acquisition Specialist", "specialty": "hiring and talent sourcing"},
            {"code": "TRAINER-01", "name": "Training & Enablement Specialist", "specialty": "employee learning and development programs"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "employment law and HR legal matters"},
        ],
        "out_of_scope_examples": ["technical support", "sales prospecting", "content creation", "bookkeeping"],
    },
    "FINANCE-01": {
        "domain_tags": ["bookkeeping", "accounting", "invoicing", "expense tracking", "financial reporting", "payroll assistance", "cash flow management"],
        "related_agents": [
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "financial data analysis and dashboards"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "financial agreements and legal compliance"},
            {"code": "COMPLIANCE-01", "name": "Regulatory Compliance & Policy Specialist", "specialty": "financial regulatory compliance"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "content creation", "sales closing"],
    },
    "LEGAL-01": {
        "domain_tags": ["contract review", "legal document drafting", "NDA review", "terms and conditions", "employment agreements", "vendor contracts", "compliance review"],
        "related_agents": [
            {"code": "COMPLIANCE-01", "name": "Regulatory Compliance & Policy Specialist", "specialty": "regulatory and policy compliance frameworks"},
            {"code": "FINANCE-01", "name": "Bookkeeping & Accounting Assistant", "specialty": "financial aspects of legal agreements"},
            {"code": "HR-01", "name": "HR & People Operations Specialist", "specialty": "employment law and people-related legal matters"},
        ],
        "out_of_scope_examples": ["technical support", "content creation", "sales prospecting", "social media"],
    },
    "PROJECT-01": {
        "domain_tags": ["project planning", "task management", "milestone tracking", "team coordination", "risk management", "agile", "scrum", "project delivery"],
        "related_agents": [
            {"code": "Assistant-01", "name": "Executive Virtual Assistant", "specialty": "administrative support within projects"},
            {"code": "SCHEDULE-01", "name": "Scheduling & Calendar Coordination Specialist", "specialty": "timeline and calendar management"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "technical delivery and infrastructure projects"},
        ],
        "out_of_scope_examples": ["technical development", "HR management", "sales closing", "content writing"],
    },
    "SCHEDULE-01": {
        "domain_tags": ["calendar management", "meeting scheduling", "availability coordination", "reminders and follow-ups", "time zone management", "recurring meetings"],
        "related_agents": [
            {"code": "Assistant-01", "name": "Executive Virtual Assistant", "specialty": "broader administrative and operational support"},
            {"code": "PROJECT-01", "name": "Project Management & Coordination Specialist", "specialty": "project timelines and milestone scheduling"},
            {"code": "EVENT-01", "name": "Event Planning & Coordination Specialist", "specialty": "event logistics and venue scheduling"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "content writing"],
    },
    "RESEARCH-01": {
        "domain_tags": ["market research", "competitive analysis", "industry reports", "business intelligence", "research synthesis", "desk research"],
        "related_agents": [
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "turning research into dashboards and BI reports"},
            {"code": "SEO-01", "name": "SEO Specialist & Content Optimizer", "specialty": "search-based market research and keyword intelligence"},
            {"code": "MEDIA-01", "name": "Public Relations & Media Relations Specialist", "specialty": "media landscape and PR-focused research"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "content creation", "sales closing"],
    },
    "CODE-01": {
        "domain_tags": ["software development", "code review", "debugging", "code quality", "programming assistance", "architecture review", "best practices"],
        "related_agents": [
            {"code": "API-01", "name": "API Integration & Developer Experience Specialist", "specialty": "API design and integration work"},
            {"code": "QA-01", "name": "Quality Assurance & Testing Specialist", "specialty": "testing and QA after development"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "deploying and shipping the code"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "legal review"],
    },
    "API-01": {
        "domain_tags": ["API integration", "developer experience", "REST APIs", "webhooks", "API documentation", "SDK usage", "third-party integrations"],
        "related_agents": [
            {"code": "CODE-01", "name": "Software Development & Code Review Specialist", "specialty": "general software development and code review"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "infrastructure hosting the APIs"},
            {"code": "WRITER-02", "name": "Technical Writing & Documentation Specialist", "specialty": "API documentation and developer guides"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "legal review"],
    },
    "DEVOPS-01": {
        "domain_tags": ["DevOps", "CI/CD pipelines", "infrastructure management", "cloud deployment", "monitoring and alerting", "containerisation", "IaC"],
        "related_agents": [
            {"code": "CODE-01", "name": "Software Development & Code Review Specialist", "specialty": "the code being deployed"},
            {"code": "SECURITY-01", "name": "Cybersecurity & Compliance Specialist", "specialty": "security hardening and compliance in infrastructure"},
            {"code": "DATA-02", "name": "Data Engineering & Pipeline Specialist", "specialty": "data infrastructure and pipeline operations"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "legal review"],
    },
    "QA-01": {
        "domain_tags": ["quality assurance", "test automation", "bug tracking", "test case design", "software testing", "regression testing", "QA processes"],
        "related_agents": [
            {"code": "CODE-01", "name": "Software Development & Code Review Specialist", "specialty": "fixing bugs identified during QA"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "CI/CD integration for automated testing"},
            {"code": "SECURITY-01", "name": "Cybersecurity & Compliance Specialist", "specialty": "security testing and penetration testing"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "legal review"],
    },
    "SECURITY-01": {
        "domain_tags": ["cybersecurity", "security audits", "vulnerability assessment", "threat modelling", "compliance frameworks", "data protection", "incident response"],
        "related_agents": [
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "implementing security in infrastructure"},
            {"code": "COMPLIANCE-01", "name": "Regulatory Compliance & Policy Specialist", "specialty": "regulatory compliance tied to security"},
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "legal obligations around data security"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "bookkeeping"],
    },
    "DATA-02": {
        "domain_tags": ["data pipelines", "ETL processes", "data warehousing", "data engineering", "big data", "analytics infrastructure", "data modelling"],
        "related_agents": [
            {"code": "DATA-01", "name": "Data Entry & Database Management Specialist", "specialty": "manual data entry and database hygiene"},
            {"code": "ANALYST-01", "name": "Business Intelligence & Analytics Specialist", "specialty": "analysing the data the pipelines deliver"},
            {"code": "DEVOPS-01", "name": "DevOps & Infrastructure Specialist", "specialty": "infrastructure running the data pipelines"},
        ],
        "out_of_scope_examples": ["HR management", "sales prospecting", "content creation", "legal review"],
    },
    "TRANSLATE-01": {
        "domain_tags": ["translation", "localisation", "multilingual content", "cultural adaptation", "language quality", "transcreation"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "original source content before translation"},
            {"code": "BRAND-01", "name": "Brand Voice & Messaging Specialist", "specialty": "maintaining brand voice across languages"},
            {"code": "MEDIA-01", "name": "Public Relations & Media Relations Specialist", "specialty": "multilingual PR and media outreach"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "ANALYST-01": {
        "domain_tags": ["business intelligence", "data analysis", "dashboards", "KPI reporting", "data visualisation", "performance metrics", "insights"],
        "related_agents": [
            {"code": "DATA-02", "name": "Data Engineering & Pipeline Specialist", "specialty": "building the data infrastructure that feeds analytics"},
            {"code": "RESEARCH-01", "name": "Business Research & Intelligence Analyst", "specialty": "qualitative research and market intelligence"},
            {"code": "FINANCE-01", "name": "Bookkeeping & Accounting Assistant", "specialty": "financial data and reporting"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "content creation", "sales closing"],
    },
    "RECRUITER-01": {
        "domain_tags": ["recruitment", "talent acquisition", "job descriptions", "candidate screening", "hiring process", "interview frameworks", "employer branding"],
        "related_agents": [
            {"code": "HR-01", "name": "HR & People Operations Specialist", "specialty": "HR policy and employee relations post-hire"},
            {"code": "TRAINER-01", "name": "Training & Enablement Specialist", "specialty": "onboarding and training new hires"},
            {"code": "COACH-01", "name": "Executive Coaching & Leadership Development Specialist", "specialty": "leadership development for new managers"},
        ],
        "out_of_scope_examples": ["technical support", "sales prospecting", "content creation", "legal contracts"],
    },
    "TRAINER-01": {
        "domain_tags": ["training programs", "learning content", "employee enablement", "onboarding training", "skill development", "LMS content", "workshops"],
        "related_agents": [
            {"code": "HR-01", "name": "HR & People Operations Specialist", "specialty": "HR strategy and workforce planning"},
            {"code": "COACH-01", "name": "Executive Coaching & Leadership Development Specialist", "specialty": "leadership and executive coaching"},
            {"code": "WRITER-02", "name": "Technical Writing & Documentation Specialist", "specialty": "writing training manuals and documentation"},
        ],
        "out_of_scope_examples": ["technical support", "sales closing", "content marketing", "legal review"],
    },
    "EVENT-01": {
        "domain_tags": ["event planning", "corporate events", "event logistics", "venue coordination", "event marketing", "conferences", "webinars"],
        "related_agents": [
            {"code": "SCHEDULE-01", "name": "Scheduling & Calendar Coordination Specialist", "specialty": "scheduling and calendar logistics for events"},
            {"code": "MEDIA-01", "name": "Public Relations & Media Relations Specialist", "specialty": "PR and media coverage around events"},
            {"code": "DESIGNER-01", "name": "Graphic Design & Visual Content Specialist", "specialty": "event collateral and visual assets"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "content writing"],
    },
    "WRITER-02": {
        "domain_tags": ["technical writing", "documentation", "user manuals", "API docs", "knowledge base articles", "release notes", "SOPs"],
        "related_agents": [
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "marketing and narrative writing"},
            {"code": "CODE-01", "name": "Software Development & Code Review Specialist", "specialty": "understanding the code being documented"},
            {"code": "API-01", "name": "API Integration & Developer Experience Specialist", "specialty": "API documentation and developer guides"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "DESIGNER-01": {
        "domain_tags": ["graphic design", "visual content", "brand assets", "infographics", "UI mockups", "presentation design", "social media visuals"],
        "related_agents": [
            {"code": "BRAND-01", "name": "Brand Voice & Messaging Specialist", "specialty": "brand guidelines and visual identity rules"},
            {"code": "SOCIAL-01", "name": "Social Media Manager", "specialty": "social media content that needs visual assets"},
            {"code": "VIDEO-01", "name": "Video Script Writer & Storyboard Specialist", "specialty": "storyboards and visual direction for video"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "COACH-01": {
        "domain_tags": ["executive coaching", "leadership development", "career coaching", "performance coaching", "team dynamics", "management training"],
        "related_agents": [
            {"code": "HR-01", "name": "HR & People Operations Specialist", "specialty": "HR strategy and performance management policy"},
            {"code": "TRAINER-01", "name": "Training & Enablement Specialist", "specialty": "structured learning programs and enablement"},
            {"code": "RECRUITER-01", "name": "Recruitment & Talent Acquisition Specialist", "specialty": "hiring the right leaders"},
        ],
        "out_of_scope_examples": ["technical support", "sales prospecting", "content creation", "legal review"],
    },
    "MEDIA-01": {
        "domain_tags": ["public relations", "media relations", "press releases", "brand reputation", "media outreach", "PR strategy", "crisis communications"],
        "related_agents": [
            {"code": "BRAND-01", "name": "Brand Voice & Messaging Specialist", "specialty": "brand messaging and positioning"},
            {"code": "Author-01", "name": "Content Writer & Storyteller", "specialty": "writing press releases and thought leadership content"},
            {"code": "SOCIAL-01", "name": "Social Media Manager", "specialty": "amplifying PR through social channels"},
        ],
        "out_of_scope_examples": ["technical support", "HR management", "sales closing", "legal review"],
    },
    "COMPLIANCE-01": {
        "domain_tags": ["regulatory compliance", "policy management", "compliance frameworks", "risk management", "auditing", "GDPR", "SOC 2", "ISO standards"],
        "related_agents": [
            {"code": "LEGAL-01", "name": "Legal Document Review & Contract Assistant", "specialty": "legal review and contract compliance"},
            {"code": "SECURITY-01", "name": "Cybersecurity & Compliance Specialist", "specialty": "security compliance and technical controls"},
            {"code": "HR-01", "name": "HR & People Operations Specialist", "specialty": "HR-related compliance and policies"},
        ],
        "out_of_scope_examples": ["technical support", "sales prospecting", "content creation", "bookkeeping"],
    },
    "ADMIN-02": {
        "domain_tags": ["office administration", "operations coordination", "administrative support", "vendor management", "facilities management", "procurement"],
        "related_agents": [
            {"code": "Assistant-01", "name": "Executive Virtual Assistant", "specialty": "executive-level administrative and scheduling support"},
            {"code": "SCHEDULE-01", "name": "Scheduling & Calendar Coordination Specialist", "specialty": "calendar and meeting coordination"},
            {"code": "PROJECT-01", "name": "Project Management & Coordination Specialist", "specialty": "coordinating operational projects"},
        ],
        "out_of_scope_examples": ["technical support", "sales closing", "content creation", "legal review"],
    },
}


ACTIVE_ROUTES = {
    "Author-01": {
        "llm_profile": {"default": "claude_opus"},
        "llm_provider": "anthropic",
        "llm_model": "claude-opus-4-5-20251101",
        "system_prompt": (
            "You are Author-01, a specialized Content Writer deployed by The CreddyPens Directorate. "
            "Your function is to produce high-quality written content including blog posts, YouTube scripts, ad copy, "
            "email sequences, and video sales letters. You write in the client's brand voice as defined in their "
            "configuration profile. You always produce well-researched, structured, and engaging content. You do not "
            "produce content that is misleading, defamatory, or violates copyright. When asked to write on a topic you "
            "do not have sufficient information about, you ask one clarifying question before proceeding."
        ),
    },
    "Assistant-01": {
        "llm_profile": {"default": "claude_sonnet"},
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5-20250929",
        "system_prompt": (
            "You are Assistant-01, a Virtual Assistant deployed by The CreddyPens Directorate. Your function is to help "
            "with email drafting, meeting scheduling, task organization, research summarization, and general operational "
            "support. You are efficient, precise, and professional. You do not make commitments on behalf of the client "
            "without explicit instruction. You do not access external systems unless the client has configured an "
            "integration. When a task is outside your capability, you say so clearly and suggest what the client should "
            "do instead."
        ),
    },
    "Greeter-01": {
        "llm_profile": {"default": "claude_sonnet"},
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5-20250929",
        "system_prompt": (
            "You are Greeter-01, an AI Receptionist deployed by The CreddyPens Directorate on behalf of the client "
            "company specified in your configuration. Your function is to handle inbound customer inquiries "
            "professionally and warmly. You answer common questions using the company information provided in your "
            "configuration. You collect the customer's name and the purpose of their inquiry. You route complex or "
            "sensitive issues by informing the customer that a team member will follow up. You never fabricate "
            "information about the company. You never discuss pricing, contracts, or legal matters unless the client "
            "has explicitly provided that information in your configuration."
        ),
    },
}

DEFAULT_ROUTE = {
    "llm_profile": {"default": "claude_sonnet"},
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4-5-20250929",
}


def build_default_system_prompt(item: dict, code: str) -> str:
    human_name = (item.get("human_name") or "").strip() or code
    role = (item.get("role") or "").strip() or "specialized AI professional"
    department = DEPARTMENT_MAP.get(str(item.get("department", "")).strip(), str(item.get("department", "")).strip() or "Directorate")
    description = (item.get("description") or "").strip()
    capabilities = item.get("capabilities") or []
    cap_lines = []
    for capability in capabilities[:8]:
        text_value = str(capability).strip()
        if text_value:
            cap_lines.append(f"- {text_value}")
    caps_text = "\n".join(cap_lines) if cap_lines else "- Execute assigned tasks accurately and professionally."

    return (
        f"You are {code} ({human_name}), a {role} in {department} at The CreddyPens Directorate.\n"
        "Operate as an elite AI employee: clear, professional, outcome-driven, and aligned to the client context.\n\n"
        f"Mission:\n{description}\n\n"
        f"Core capabilities:\n{caps_text}\n\n"
        "Safety boundaries:\n"
        "- Do not provide definitive legal advice, financial advice, or medical diagnosis.\n"
        "- Do not fabricate facts, policies, or pricing details that were not provided by the client.\n"
        "- If asked to act outside your scope, state the limitation clearly and suggest the right escalation path.\n"
    ).strip()


def load_dossiers() -> list[dict]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dossier data file not found: {DATA_PATH}")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Dossier data is empty or invalid")
    return data


def to_seed_row(item: dict) -> dict:
    code = canonical_code(str(item.get("code", "")).strip())
    route = ACTIVE_ROUTES.get(code, DEFAULT_ROUTE)
    system_prompt = route.get("system_prompt") or build_default_system_prompt(item, code)
    domain = AGENT_DOMAIN_DATA.get(code, {})
    return {
        "agent_id": code.lower(),
        "code": code,
        "name": str(item.get("role", "")).strip() or code,
        "human_name": str(item.get("human_name", "")).strip() or None,
        "tagline": str(item.get("tagline", "")).strip() or None,
        "description": str(item.get("description", "")).strip() or "",
        "profile": str(item.get("profile", "")).strip() or "",
        "capabilities": item.get("capabilities") or [],
        "operational_sections": item.get("operational_sections") or [],
        "ideal_for": str(item.get("ideal_for", "")).strip() or None,
        "personality": str(item.get("personality", "")).strip() or None,
        "communication_style": str(item.get("communication_style", "")).strip() or None,
        "department": DEPARTMENT_MAP.get(str(item.get("department", "")).strip(), str(item.get("department", "")).strip()),
        "price_cents": int(item.get("price_cents") or 0),
        "status": "active",
        "llm_profile": route["llm_profile"],
        "llm_provider": route["llm_provider"],
        "llm_model": route["llm_model"],
        "system_prompt": system_prompt,
        "domain_tags": domain.get("domain_tags", []),
        "related_agents": domain.get("related_agents", []),
        "out_of_scope_examples": domain.get("out_of_scope_examples", []),
    }


def main() -> None:
    ensure_schema(engine)
    dossiers = load_dossiers()
    rows = [to_seed_row(item) for item in dossiers]
    expected_agent_ids = [row["agent_id"] for row in rows]

    ensure_columns_sql = text(
        """
        alter table if exists agent_catalog add column if not exists human_name text;
        alter table if exists agent_catalog add column if not exists tagline text;
        alter table if exists agent_catalog add column if not exists profile text not null default '';
        alter table if exists agent_catalog add column if not exists capabilities jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists operational_sections jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists ideal_for text;
        alter table if exists agent_catalog add column if not exists personality text;
        alter table if exists agent_catalog add column if not exists communication_style text;
        alter table if exists agent_catalog add column if not exists domain_tags jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists related_agents jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists out_of_scope_examples jsonb not null default '[]'::jsonb;
        """
    )
    delete_stale_agents_sql = text("delete from agent_catalog where agent_id not in :agent_ids").bindparams(
        bindparam("agent_ids", expanding=True)
    )

    upsert_agent_sql = text(
        """
        insert into agent_catalog
          (
            agent_id, code, name, human_name, tagline, description, profile, capabilities, operational_sections,
            ideal_for, personality, communication_style, department, price_cents, status,
            llm_profile, llm_provider, llm_model, system_prompt,
            domain_tags, related_agents, out_of_scope_examples
          )
        values
          (
            :agent_id, :code, :name, :human_name, :tagline, :description, :profile,
            cast(:capabilities as jsonb), cast(:operational_sections as jsonb),
            :ideal_for, :personality, :communication_style, :department, :price_cents, :status,
            cast(:llm_profile as jsonb), :llm_provider, :llm_model, :system_prompt,
            cast(:domain_tags as jsonb), cast(:related_agents as jsonb), cast(:out_of_scope_examples as jsonb)
          )
        on conflict (agent_id) do update set
          code = excluded.code,
          name = excluded.name,
          human_name = excluded.human_name,
          tagline = excluded.tagline,
          description = excluded.description,
          profile = excluded.profile,
          capabilities = excluded.capabilities,
          operational_sections = excluded.operational_sections,
          ideal_for = excluded.ideal_for,
          personality = excluded.personality,
          communication_style = excluded.communication_style,
          department = excluded.department,
          price_cents = excluded.price_cents,
          status = excluded.status,
          llm_profile = excluded.llm_profile,
          llm_provider = excluded.llm_provider,
          llm_model = excluded.llm_model,
          system_prompt = excluded.system_prompt,
          domain_tags = excluded.domain_tags,
          related_agents = excluded.related_agents,
          out_of_scope_examples = excluded.out_of_scope_examples,
          updated_at = now();
        """
    )

    upsert_org_sql = text(
        """
        insert into organizations (org_id, name)
        values (:org_id, :name)
        on conflict (org_id) do update set
          name = excluded.name;
        """
    )

    upsert_hired_sql = text(
        """
        insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
        values (:hired_agent_id, :org_id, :agent_code, :status, cast(:configuration as jsonb))
        on conflict (org_id, agent_code) do update set
          status = excluded.status,
          configuration = excluded.configuration,
          updated_at = now();
        """
    )

    upsert_user_sql = text(
        """
        insert into users (user_id, org_id, email)
        values (:user_id, :org_id, :email)
        on conflict (user_id) do update set
          org_id = excluded.org_id,
          email = excluded.email;
        """
    )

    with engine.begin() as conn:
        conn.execute(ensure_columns_sql)
        conn.execute(delete_stale_agents_sql, {"agent_ids": expected_agent_ids})
        for row in rows:
            payload = {
                **row,
                "capabilities": json.dumps(row["capabilities"]),
                "operational_sections": json.dumps(row["operational_sections"]),
                "llm_profile": json.dumps(row["llm_profile"]),
                "domain_tags": json.dumps(row["domain_tags"]),
                "related_agents": json.dumps(row["related_agents"]),
                "out_of_scope_examples": json.dumps(row["out_of_scope_examples"]),
            }
            conn.execute(upsert_agent_sql, payload)

        # Dev org + hires (v1 launch trio)
        conn.execute(upsert_org_sql, {"org_id": "org_test", "name": "Test Organization"})
        conn.execute(upsert_user_sql, {"user_id": "user_test", "org_id": "org_test", "email": "test@example.com"})
        for code in ["Author-01", "Assistant-01", "Greeter-01"]:
            conn.execute(
                upsert_hired_sql,
                {
                    "hired_agent_id": str(uuid.uuid4()),
                    "org_id": "org_test",
                    "agent_code": code,
                    "status": "active",
                    "configuration": json.dumps(
                        {
                            "company_name": "TestCo",
                            "tone": "professional",
                            "additional": {},
                        }
                    ),
                },
            )

    print(f"Seeded {len(rows)} agents from {DATA_PATH.name}")


if __name__ == "__main__":
    main()
