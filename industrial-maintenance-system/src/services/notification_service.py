"""
Notification Service: Delivers instant alerts to technicians' mobile phones and tablets
via Telegram Bot API and generic Webhooks (WhatsApp/Discord/Custom).
Zero external dependencies required (uses Python standard library urllib.request).
"""

from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class NotificationService:
    """Manages dispatching alerts to mobile devices and messaging platforms."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            data_dir = BASE_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = data_dir / "notifications_config.json"
        else:
            self.config_path = Path(config_path)

        self.history: List[Dict[str, Any]] = []
        self._load_config()

    def _load_config(self) -> None:
        """Loads or initializes notification settings."""
        if not self.config_path.exists():
            default_config = {
                "enabled": False,
                "telegram_enabled": False,
                "telegram_bot_token": "",
                "telegram_chat_id": "",
                "webhook_enabled": False,
                "webhook_url": "",
            }
            self.save_config(default_config)
            self.config = default_config
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception:
                self.config = {"enabled": False}

    def save_config(self, new_config: Dict[str, Any]) -> None:
        """Saves updated notification configuration to JSON."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        self.config = new_config

    def get_public_config(self) -> Dict[str, Any]:
        """Returns config with secret tokens masked for UI display."""
        cfg = dict(self.config)
        token = cfg.get("telegram_bot_token", "")
        if token and len(token) > 8:
            cfg["telegram_bot_token"] = token[:4] + "..." + token[-4:]
        return cfg

    def send_work_order_alert(
        self, work_order: Any, direct_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats and dispatches a high-priority mobile alert for a new/emergency Work Order.
        Returns status result dictionary.
        """
        now = datetime.now().strftime("%H:%M:%S")
        wo_id = getattr(work_order, "id", "N/A")
        eq_code = getattr(work_order, "equipment_code", "N/A")
        title = getattr(work_order, "title", "Sin título")
        prio = getattr(work_order, "priority", "MEDIUM")
        wo_type = getattr(work_order, "type", "CORRECTIVE")
        tech = getattr(work_order, "assigned_technician", "Técnico de Turno")

        link_text = f"\n📱 <b>Toca aquí para ver en tu tablet/móvil:</b>\n{direct_url}" if direct_url else ""

        message_html = (
            f"🚨 <b>NUEVA ORDEN DE TRABAJO OT #{wo_id}</b>\n"
            f"────────────────────────\n"
            f"🛠️ <b>Activo:</b> {eq_code}\n"
            f"⚠️ <b>Prioridad:</b> {prio} | <b>Tipo:</b> {wo_type}\n"
            f"📋 <b>Asunto:</b> {title}\n"
            f"👷 <b>Técnico Asignado:</b> {tech}\n"
            f"⏱️ <b>Hora:</b> {now}\n"
            f"{link_text}"
        )

        plain_message = (
            f"🚨 NUEVA ORDEN DE TRABAJO OT #{wo_id}\n"
            f"Activo: {eq_code} | Prioridad: {prio} | Tipo: {wo_type}\n"
            f"Asunto: {title}\n"
            f"Técnico Asignado: {tech}\n"
            f"{direct_url if direct_url else ''}"
        )

        # Log into in-memory history
        log_entry = {
            "timestamp": now,
            "work_order_id": wo_id,
            "technician": tech,
            "message": plain_message,
            "telegram_sent": False,
            "webhook_sent": False,
        }

        # 1. Telegram Dispatch
        if self.config.get("enabled") and self.config.get("telegram_enabled"):
            token = self.config.get("telegram_bot_token", "").strip()
            chat_id = self.config.get("telegram_chat_id", "").strip()
            if token and chat_id:
                success, err = self._dispatch_telegram(token, chat_id, message_html)
                log_entry["telegram_sent"] = success
                if err:
                    log_entry["telegram_error"] = err

        # 2. Webhook Dispatch (WhatsApp gateway / Zapier / Make / n8n)
        if self.config.get("enabled") and self.config.get("webhook_enabled"):
            webhook_url = self.config.get("webhook_url", "").strip()
            if webhook_url:
                payload = {
                    "event": "new_work_order",
                    "work_order": asdict(work_order) if hasattr(work_order, "__dataclass_fields__") else {},
                    "technician": tech,
                    "url": direct_url,
                    "message": plain_message,
                }
                success, err = self._dispatch_webhook(webhook_url, payload)
                log_entry["webhook_sent"] = success
                if err:
                    log_entry["webhook_error"] = err

        self.history.insert(0, log_entry)
        if len(self.history) > 50:
            self.history.pop()

        return log_entry

    def send_test_notification(self, test_url: str = "http://localhost:5000/tecnico") -> Dict[str, Any]:
        """Sends a verification message to ensure mobile delivery works."""
        test_msg = (
            f"✅ <b>PRUEBA DE CONEXIÓN CMMS INDUSTRIAL</b>\n"
            f"────────────────────────\n"
            f"Este es un mensaje de prueba para técnicos y tablets corporativas.\n"
            f"📱 Enlace de prueba: {test_url}"
        )

        result = {"success": True, "details": []}

        if self.config.get("telegram_enabled"):
            token = self.config.get("telegram_bot_token", "").strip()
            chat_id = self.config.get("telegram_chat_id", "").strip()
            if token and chat_id:
                ok, err = self._dispatch_telegram(token, chat_id, test_msg)
                result["details"].append({"channel": "telegram", "success": ok, "error": err})
            else:
                result["details"].append({"channel": "telegram", "success": False, "error": "Token o Chat ID faltante"})

        if self.config.get("webhook_enabled"):
            webhook_url = self.config.get("webhook_url", "").strip()
            if webhook_url:
                ok, err = self._dispatch_webhook(webhook_url, {"event": "test", "text": "Prueba CMMS"})
                result["details"].append({"channel": "webhook", "success": ok, "error": err})

        return result

    def _dispatch_telegram(self, token: str, chat_id: str, html_text: str) -> tuple[bool, Optional[str]]:
        """Sends an HTML formatted message via Telegram Bot API."""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": html_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as res:
                return (res.status == 200, None)
        except Exception as e:
            return (False, str(e))

    def _dispatch_webhook(self, webhook_url: str, payload_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Sends a JSON payload to an external HTTP webhook."""
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload_dict).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as res:
                return (res.status in (200, 201, 202, 204), None)
        except Exception as e:
            return (False, str(e))
