import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
import logging

logger = logging.getLogger(__name__)


def _send_email_base(to_email: str, subject: str, html_body: str) -> dict:
    """
    Base helper: sends an HTML email via Gmail SMTP (TLS on port 587).
    Prints full diagnostic logs to terminal for debugging.
    """
    # ── Pre-flight checks ────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  AS PLANTS EMAIL SEND ATTEMPT")
    print("=" * 55)
    print(f"  To       : {to_email}")
    print(f"  Subject  : {subject}")
    print(f"  SMTP Host: {settings.SMTP_SERVER}")
    print(f"  SMTP Port: {settings.SMTP_PORT}")
    print(f"  Username : {settings.SMTP_SENDER!r}")
    passwd_raw = settings.SMTP_PASSWORD or ""
    passwd = passwd_raw.replace(" ", "")
    print(f"  Password : {'(empty)' if not passwd else passwd[:4] + '...' + passwd[-4:] + f' (len={len(passwd)})'}")
    print("=" * 55)

    if not settings.SMTP_SERVER:
        msg = "SMTP_HOST is not set in env.txt"
        print(f"[EMAIL] ERROR: {msg}")
        return {"success": False, "message": msg}

    if not settings.SMTP_SENDER:
        msg = "SMTP_USERNAME is not set in env.txt"
        print(f"[EMAIL] ERROR: {msg}")
        return {"success": False, "message": msg}

    if not passwd:
        msg = "SMTP_PASSWORD is not set in env.txt"
        print(f"[EMAIL] ERROR: {msg}")
        return {"success": False, "message": msg}

    # ── Build message ────────────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    display_name = getattr(settings, "SMTP_DISPLAY_NAME", "") or ""
    msg["From"] = f"{display_name} <{settings.SMTP_SENDER}>" if display_name else settings.SMTP_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # ── Send ─────────────────────────────────────────────────────────────────
    try:
        print(f"[EMAIL] Connecting to {settings.SMTP_SERVER}:{settings.SMTP_PORT} ...")
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            print("[EMAIL] EHLO OK")

            server.starttls()
            server.ehlo()
            print("[EMAIL] STARTTLS OK")

            print(f"[EMAIL] Authenticating as {settings.SMTP_SENDER} ...")
            try:
                server.login(settings.SMTP_SENDER, passwd)
                print("[EMAIL] LOGIN OK")
            except smtplib.SMTPAuthenticationError as auth_err:
                raw = auth_err.smtp_error
                detail = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(auth_err)
                err_msg = f"SMTP Auth Failed (code {auth_err.smtp_code}): {detail}"
                print(f"[EMAIL] AUTH ERROR: {err_msg}")
                print("[EMAIL] FIX: Re-generate Gmail App Password at https://myaccount.google.com/apppasswords")
                logger.error(err_msg)
                return {"success": False, "message": err_msg}

            print(f"[EMAIL] Sending to {to_email} ...")
            server.sendmail(settings.SMTP_SENDER, [to_email], msg.as_string())
            print(f"[EMAIL] ✅ Email sent successfully to {to_email}")
            logger.info(f"Email sent successfully to {to_email}")
            return {"success": True, "message": "Email sent successfully"}

    except smtplib.SMTPConnectError as conn_err:
        err_msg = f"SMTP Connection Failed: {conn_err}"
        print(f"[EMAIL] CONNECTION ERROR: {err_msg}")
        logger.error(err_msg)
        return {"success": False, "message": err_msg}

    except Exception as e:
        err_msg = f"Failed to send email: {type(e).__name__}: {e}"
        print(f"[EMAIL] UNEXPECTED ERROR: {err_msg}")
        print(traceback.format_exc())
        logger.error(err_msg)
        return {"success": False, "message": err_msg}




def send_otp_email(to_email: str, otp: str) -> dict:
    """
    Sends a premium HTML OTP verification email to the customer.
    """
    subject = "Your AS Plants Verification Code"
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AS Plants OTP</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f7f3;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f3;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">
              <p style="margin:0 0 6px;font-size:28px;font-weight:800;color:#ffffff;letter-spacing:1px;">&#127807; AS Plants</p>
              <p style="margin:0;font-size:13px;color:#a8d5b5;letter-spacing:0.5px;">Bring Nature Home</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 20px;">
              <p style="margin:0 0 8px;font-size:20px;font-weight:700;color:#1B3B2B;">Email Verification</p>
              <p style="margin:0 0 28px;font-size:14px;color:#6b7b72;line-height:1.6;">
                To securely create your AS Plants account, please use the following One-Time Password (OTP):
              </p>

              <!-- OTP Box -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="background:#f0f7f3;border:2px dashed #2E6B4F;border-radius:16px;padding:28px 0;">
                    <p style="margin:0;font-size:42px;font-weight:800;letter-spacing:12px;color:#1B3B2B;font-family:'Courier New',monospace;">{otp}</p>
                  </td>
                </tr>
              </table>

              <p style="margin:24px 0 0;font-size:13px;color:#6b7b72;text-align:center;">
                This code is valid for <strong style="color:#1B3B2B;">5 minutes</strong>.
                If you didn't request this, please ignore this email.
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e8f0eb;margin:0;"/>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 32px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#a0b0a8;">
                &#128274; Secure &nbsp;&bull;&nbsp; Trusted &nbsp;&bull;&nbsp; Reliable
              </p>
              <p style="margin:8px 0 0;font-size:11px;color:#c0ccc5;">
                &copy; 2025 AS Plants. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    result = _send_email_base(to_email, subject, html_body)
    if not result["success"]:
        return {"success": False, "message": result["message"]}
    return result


def send_welcome_email(to_email: str, name: str) -> dict:
    """
    Sends a welcome HTML email upon successful registration.
    """
    subject = "Welcome to AS Plants! &#127807;"
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f0f7f3;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f3;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">
              <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">&#127807; AS Plants</p>
              <p style="margin:0;font-size:13px;color:#a8d5b5;">Bring Nature Home</p>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 40px;">
              <p style="margin:0 0 12px;font-size:20px;font-weight:700;color:#1B3B2B;">Welcome, {name}! &#127881;</p>
              <p style="font-size:14px;color:#6b7b72;line-height:1.7;">
                Your AS Plants account has been created successfully.<br/>
                You can now browse our premium plant catalog, place orders, and track deliveries.
              </p>
              <p style="font-size:14px;color:#2E6B4F;font-weight:600;">Happy Planting! &#127807;</p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 40px 28px;text-align:center;">
              <p style="margin:0;font-size:11px;color:#c0ccc5;">&copy; 2025 AS Plants. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return _send_email_base(to_email, subject, html_body)


def send_password_reset_email(to_email: str, token: str) -> dict:
    """
    Sends a password reset code to the user.
    """
    subject = "AS Plants Password Reset Request"
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f0f7f3;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f3;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">
              <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">&#127807; AS Plants</p>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 40px;">
              <p style="margin:0 0 12px;font-size:20px;font-weight:700;color:#1B3B2B;">Password Reset</p>
              <p style="font-size:14px;color:#6b7b72;line-height:1.7;">
                We received a request to reset your AS Plants password. Use this code:
              </p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="background:#f0f7f3;border:2px dashed #2E6B4F;border-radius:16px;padding:24px 0;">
                    <p style="margin:0;font-size:36px;font-weight:800;letter-spacing:10px;color:#1B3B2B;font-family:'Courier New',monospace;">{token}</p>
                  </td>
                </tr>
              </table>
              <p style="font-size:13px;color:#6b7b72;text-align:center;margin-top:20px;">
                If you didn't request this, please ignore this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 40px 28px;text-align:center;">
              <p style="margin:0;font-size:11px;color:#c0ccc5;">&copy; 2025 AS Plants. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return _send_email_base(to_email, subject, html_body)
