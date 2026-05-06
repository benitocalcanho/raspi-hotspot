"""
Email sending utility for notifications.
"""
import smtplib
from email.mime.text import MIMEText
from flask import current_app

def send_notification_email(subject: str, body: str):
    smtp_host = current_app.config.get("SMTP_HOST")
    smtp_port = int(current_app.config.get("SMTP_PORT", 587))
    smtp_user = current_app.config.get("SMTP_USER")
    smtp_pass = current_app.config.get("SMTP_PASS")
    sender = current_app.config.get("EMAIL_SENDER")
    recipient = current_app.config.get("EMAIL_RECIPIENT")
    print(f"[Email Debug] SMTP_HOST={smtp_host}")
    print(f"[Email Debug] SMTP_PORT={smtp_port}")
    print(f"[Email Debug] SMTP_USER={smtp_user}")
    print(f"[Email Debug] SMTP_PASS={'***' if smtp_pass else None}")
    print(f"[Email Debug] EMAIL_SENDER={sender}")
    print(f"[Email Debug] EMAIL_RECIPIENT={recipient}")
    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, sender, recipient]):
        print("[Email Debug] Missing SMTP or email config!")
        raise RuntimeError("Missing SMTP or email config.")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender, [recipient], msg.as_string())
        print("[Email Debug] Email sent successfully.")
    except Exception as e:
        print(f"[Email Debug] Exception: {e}")
        raise
