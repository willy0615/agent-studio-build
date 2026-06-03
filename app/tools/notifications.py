"""通知工具 - 邮件、Webhook、桌面通知"""
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_server: str = None,
    smtp_port: int = None,
    username: str = None,
    password: str = None,
    from_addr: str = None,
    html: bool = False
) -> Dict[str, Any]:
    """Send email notification.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        smtp_server: SMTP server (default: from config)
        smtp_port: SMTP port (default: 587)
        username: SMTP username
        password: SMTP password
        from_addr: From address (default: username)
        html: Whether body is HTML
    
    Returns:
        {
            "success": bool,
            "message_id": str,
            "error": str (if failed)
        }
    """
    try:
        # Try to load config
        config = _load_notification_config()
        
        smtp_server = smtp_server or config.get("email", {}).get("smtp_server")
        smtp_port = smtp_port or config.get("email", {}).get("smtp_port", 587)
        username = username or config.get("email", {}).get("username")
        password = password or config.get("email", {}).get("password")
        from_addr = from_addr or username
        
        if not all([smtp_server, username, password]):
            return {
                "success": False,
                "error": "Email not configured. Add email settings to config or parameters.",
            }
        
        # Create message
        msg = MIMEMultipart("alternative") if html else MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        
        if html:
            msg.attach(MIMEText(body, "html"))
        
        # Send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        
        return {
            "success": True,
            "message_id": msg["Message-ID"],
        }
    
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return {"success": False, "error": str(e)}


def send_webhook(
    url: str,
    data: Dict[str, Any],
    headers: Dict[str, str] = None,
    method: str = "POST"
) -> Dict[str, Any]:
    """Send webhook notification.
    
    Args:
        url: Webhook URL
        data: Data to send
        headers: Optional headers
        method: HTTP method (POST, PUT, PATCH)
    
    Returns:
        {
            "success": bool,
            "status_code": int,
            "error": str (if failed)
        }
    """
    try:
        import requests
        
        headers = headers or {"Content-Type": "application/json"}
        
        if method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers)
        else:
            response = requests.post(url, json=data, headers=headers)
        
        return {
            "success": response.ok,
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else None,
        }
    
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        return {"success": False, "error": str(e)}


def send_desktop_notification(
    title: str,
    message: str,
    timeout: int = 10
) -> Dict[str, Any]:
    """Send desktop notification.
    
    Args:
        title: Notification title
        message: Notification message
        timeout: Notification timeout (seconds)
    
    Returns:
        {
            "success": bool,
            "error": str (if failed)
        }
    """
    try:
        # Method 1: plyer (cross-platform)
        try:
            from plyer import notification
            
            notification.notify(
                title=title,
                message=message,
                app_name="Agent",
                timeout=timeout,
            )
            
            return {"success": True}
        
        except ImportError:
            pass
        
        # Method 2: win10toast (Windows only)
        try:
            from win10toast import ToastNotifier
            
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=timeout)
            
            return {"success": True}
        
        except ImportError:
            pass
        
        # Method 3: macOS terminal-notifier
        import platform
        if platform.system() == "Darwin":
            import subprocess
            
            subprocess.run([
                "terminal-notifier",
                "-title", title,
                "-message", message
            ])
            
            return {"success": True}
        
        return {
            "success": False,
            "error": "No desktop notification library available. Install: pip install plyer",
        }
    
    except Exception as e:
        logger.error(f"Desktop notification failed: {e}")
        return {"success": False, "error": str(e)}


def send_slack_message(
    webhook_url: str,
    text: str,
    channel: str = None,
    username: str = "Agent",
    blocks: list = None
) -> Dict[str, Any]:
    """Send Slack message via webhook.
    
    Args:
        webhook_url: Slack webhook URL
        text: Message text
        channel: Target channel (optional)
        username: Bot username
        blocks: Slack blocks for rich formatting
    
    Returns:
        {
            "success": bool,
            "error": str (if failed)
        }
    """
    try:
        import requests
        
        payload = {
            "text": text,
            "username": username,
        }
        
        if channel:
            payload["channel"] = channel
        
        if blocks:
            payload["blocks"] = blocks
        
        response = requests.post(webhook_url, json=payload)
        
        return {
            "success": response.ok,
            "status_code": response.status_code,
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "Markdown"
) -> Dict[str, Any]:
    """Send Telegram message.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Target chat ID
        text: Message text
        parse_mode: Parse mode (Markdown, HTML)
    
    Returns:
        {
            "success": bool,
            "message_id": int,
            "error": str (if failed)
        }
    """
    try:
        import requests
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        
        data = response.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "message_id": data["result"]["message_id"],
            }
        else:
            return {
                "success": False,
                "error": data.get("description"),
            }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_discord_webhook(
    webhook_url: str,
    content: str,
    username: str = "Agent",
    embeds: list = None
) -> Dict[str, Any]:
    """Send Discord message via webhook.
    
    Args:
        webhook_url: Discord webhook URL
        content: Message content
        username: Bot username
        embeds: Discord embeds for rich formatting
    
    Returns:
        {
            "success": bool,
            "error": str (if failed)
        }
    """
    try:
        import requests
        
        payload = {
            "content": content,
            "username": username,
        }
        
        if embeds:
            payload["embeds"] = embeds
        
        response = requests.post(webhook_url, json=payload)
        
        return {
            "success": response.status_code in [200, 204],
            "status_code": response.status_code,
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def _load_notification_config() -> Dict[str, Any]:
    """Load notification configuration."""
    try:
        config_path = "E:/AgentProject/data/config/notifications.json"
        if Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)
    except:
        pass
    
    return {}


# Config template
NOTIFICATION_CONFIG_TEMPLATE = {
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-app-password",
    },
    "slack": {
        "webhook_url": "https://hooks.slack.com/services/...",
    },
    "telegram": {
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID",
    },
    "discord": {
        "webhook_url": "https://discord.com/api/webhooks/...",
    }
}
