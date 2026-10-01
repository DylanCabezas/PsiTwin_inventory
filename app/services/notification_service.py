from __future__ import annotations

import asyncio
import os
import smtplib
from email.message import EmailMessage
from typing import Any

from app.database.mongodb import get_database


class NotificationService:
    """Notifica al responsable sin bloquear el flujo si SMTP no esta configurado."""

    async def notify_owner(
        self,
        id_empresa: str,
        subject: str,
        body: str
    ) -> dict[str, Any]:
        database = get_database()
        empresa = await database["empresas"].find_one(
            {
                "$or": [
                    {"id_empresa": id_empresa},
                    {"id": id_empresa}
                ]
            },
            {"_id": 0, "correo": 1}
        )

        recipient = (empresa or {}).get("correo")
        if not recipient:
            return {
                "status": "PENDIENTE",
                "reason": "La empresa no tiene correo configurado"
            }

        smtp_host = os.getenv("PSITWIN_SMTP_HOST")
        smtp_port = int(os.getenv("PSITWIN_SMTP_PORT", "587"))
        smtp_user = os.getenv("PSITWIN_SMTP_USER")
        smtp_password = os.getenv("PSITWIN_SMTP_PASSWORD")
        smtp_from = os.getenv("PSITWIN_SMTP_FROM", smtp_user or "")

        if not all((smtp_host, smtp_user, smtp_password, smtp_from)):
            return {
                "status": "PENDIENTE",
                "recipient": recipient,
                "reason": "SMTP no configurado"
            }

        await asyncio.to_thread(
            self._send,
            smtp_host,
            smtp_port,
            smtp_user,
            smtp_password,
            smtp_from,
            recipient,
            subject,
            body
        )
        return {
            "status": "ENVIADO",
            "recipient": recipient
        }

    @staticmethod
    def _send(
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        recipient: str,
        subject: str,
        body: str
    ) -> None:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
