from app.integrations.email import EmailIntegration, email_integration
from app.integrations.slack import SlackIntegration, slack_integration
from app.integrations.webhook import WebhookIntegration, webhook_integration

__all__ = [
    "SlackIntegration",
    "slack_integration",
    "EmailIntegration",
    "email_integration",
    "WebhookIntegration",
    "webhook_integration",
]
