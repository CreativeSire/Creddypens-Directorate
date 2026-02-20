from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib


class EmailIntegration:
    async def send_email(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        use_tls: bool = True,
    ) -> dict:
        if not smtp_host.strip() or not to_email.strip():
            raise ValueError("Missing SMTP host or recipient")

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=int(smtp_port),
            username=smtp_user,
            password=smtp_password,
            use_tls=use_tls,
            timeout=20,
        )
        return {"ok": True}

    def send_email_sync(self, **kwargs) -> dict:
        import asyncio

        return asyncio.run(self.send_email(**kwargs))


email_integration = EmailIntegration()
