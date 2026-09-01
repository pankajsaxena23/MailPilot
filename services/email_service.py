import os
import time
import smtplib
from email.mime.text import MIMEText

def send_email_campaign(subject, body, recipients, delay_seconds=1.0, max_retries=2):
    """
    Sends an email campaign to a list of recipients via SMTP (e.g. Gmail).
    Reads SMTP credentials and host configuration from environment variables.
    """
    sender_email = os.environ.get("SMTP_EMAIL")
    sender_password = os.environ.get("eaot uccf pswv ovzq")
    sender_name = os.environ.get("SMTP_SENDER_NAME", "MailPilot")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not sender_email or not sender_password or sender_email == "your_email@gmail.com":
        return {
            "success": False,
            "error": "SMTP credentials are not configured properly. Please set SMTP_EMAIL and SMTP_PASSWORD in your .env file."
        }

    # Guard against a string accidentally being passed instead of a list
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    if not recipients:
        return {"success": False, "error": "No recipients provided."}

    results = []
    server = None

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls()
        server.login(sender_email, sender_password)

        for recipient in recipients:
            msg = MIMEText(body, "plain", "utf-8")
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = recipient
            msg["Subject"] = subject

            attempt = 0
            sent = False
            last_error = None

            while attempt <= max_retries and not sent:
                try:
                    server.sendmail(sender_email, recipient, msg.as_string())
                    sent = True
                except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
                    last_error = str(e)
                    try:
                        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                        server.starttls()
                        server.login(sender_email, sender_password)
                    except Exception as reconnect_err:
                        last_error = str(reconnect_err)
                        break
                except Exception as e:
                    last_error = str(e)
                    break
                attempt += 1

            if sent:
                results.append({"email": recipient, "status": "Sent"})
            else:
                results.append({"email": recipient, "status": "Failed", "error": last_error})

            time.sleep(delay_seconds)

        return {"success": True, "results": results}

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
