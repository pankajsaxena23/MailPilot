import os
import time
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_email_campaign(
    subject,
    body,
    recipients,
    delay_seconds=1.0,
    max_retries=2
):
    """
    Send an email campaign to multiple recipients using SMTP.

    SMTP configuration is loaded from environment variables:

        SMTP_EMAIL
        SMTP_PASSWORD
        SMTP_SENDER_NAME
        SMTP_SERVER
        SMTP_PORT
    """

    # ========================================================
    # SMTP CONFIGURATION
    # ========================================================

    sender_email = os.environ.get(
        "SMTP_EMAIL",
        ""
    ).strip()

    sender_password = os.environ.get(
        "SMTP_PASSWORD",
        ""
    ).strip()

    sender_name = os.environ.get(
        "SMTP_SENDER_NAME",
        "MailPilot"
    ).strip()

    smtp_server = os.environ.get(
        "SMTP_SERVER",
        "smtp.gmail.com"
    ).strip()

    try:
        smtp_port = int(
            os.environ.get(
                "SMTP_PORT",
                "587"
            )
        )
    except ValueError:
        return {
            "success": False,
            "error": "SMTP_PORT must be a valid number."
        }

    # ========================================================
    # VALIDATE SMTP CONFIGURATION
    # ========================================================

    if not sender_email:
        return {
            "success": False,
            "error": (
                "SMTP_EMAIL is not configured. "
                "Please add SMTP_EMAIL to your .env file."
            )
        }

    if not sender_password:
        return {
            "success": False,
            "error": (
                "SMTP_PASSWORD is not configured. "
                "Please add SMTP_PASSWORD to your .env file."
            )
        }

    # ========================================================
    # NORMALIZE RECIPIENTS
    # ========================================================

    if isinstance(recipients, str):

        recipients = [
            email.strip()
            for email in recipients.split(",")
            if email.strip()
        ]

    elif isinstance(recipients, list):

        recipients = [
            str(email).strip()
            for email in recipients
            if str(email).strip()
        ]

    else:

        return {
            "success": False,
            "error": "Recipients must be a list or comma-separated string."
        }

    if not recipients:
        return {
            "success": False,
            "error": "No recipients provided."
        }

    # Remove duplicate recipients
    recipients = list(
        dict.fromkeys(
            email.lower()
            for email in recipients
        )
    )

    results = []
    server = None

    # ========================================================
    # CONNECT TO SMTP SERVER
    # ========================================================

    def connect_smtp():
        """
        Create and authenticate an SMTP connection.
        """

        smtp = smtplib.SMTP(
            smtp_server,
            smtp_port,
            timeout=30
        )

        smtp.ehlo()

        smtp.starttls()

        smtp.ehlo()

        smtp.login(
            sender_email,
            sender_password
        )

        return smtp

    # ========================================================
    # MAIN SEND PROCESS
    # ========================================================

    try:

        server = connect_smtp()

        for index, recipient in enumerate(recipients):

            msg = MIMEText(
                body,
                "plain",
                "utf-8"
            )

            msg["From"] = formataddr(
                (sender_name, sender_email)
            )

            msg["To"] = recipient

            msg["Subject"] = subject

            sent = False
            last_error = None

            # ------------------------------------------------
            # RETRY
            # ------------------------------------------------

            for attempt in range(max_retries + 1):

                try:

                    server.sendmail(
                        sender_email,
                        [recipient],
                        msg.as_string()
                    )

                    sent = True
                    break

                except (
                    smtplib.SMTPServerDisconnected,
                    smtplib.SMTPConnectError,
                    smtplib.SMTPResponseException,
                    smtplib.SMTPException
                ) as e:

                    last_error = str(e)

                    # Reconnect before retry
                    if attempt < max_retries:

                        try:

                            if server is not None:
                                try:
                                    server.quit()
                                except Exception:
                                    pass

                            server = connect_smtp()

                        except Exception as reconnect_error:

                            last_error = str(
                                reconnect_error
                            )

                            time.sleep(1)

                except Exception as e:

                    last_error = str(e)
                    break

            # ------------------------------------------------
            # STORE RESULT
            # ------------------------------------------------

            if sent:

                results.append({
                    "email": recipient,
                    "status": "Sent"
                })

            else:

                results.append({
                    "email": recipient,
                    "status": "Failed",
                    "error": last_error or "Unknown SMTP error"
                })

            # ------------------------------------------------
            # DELAY BETWEEN EMAILS
            # ------------------------------------------------

            if index < len(recipients) - 1:
                time.sleep(
                    max(0, float(delay_seconds))
                )

        # ====================================================
        # FINAL RESULT
        # ====================================================

        successful = sum(
            1
            for result in results
            if result["status"] == "Sent"
        )

        failed = len(results) - successful

        return {
            "success": successful > 0,
            "results": results,
            "total": len(results),
            "sent": successful,
            "failed": failed
        }

    except smtplib.SMTPAuthenticationError:

        return {
            "success": False,
            "results": results,
            "error": (
                "SMTP authentication failed. "
                "For Gmail, use a Gmail App Password "
                "instead of your normal Gmail password."
            )
        }

    except (
        smtplib.SMTPConnectError,
        smtplib.SMTPServerDisconnected,
        smtplib.SMTPException
    ) as e:

        return {
            "success": False,
            "results": results,
            "error": f"SMTP error: {str(e)}"
        }

    except Exception as e:

        return {
            "success": False,
            "results": results,
            "error": str(e)
        }

    finally:

        if server is not None:

            try:
                server.quit()
            except Exception:
                pass
