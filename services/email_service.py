import os
import traceback
import requests
import logging

from config import settings

logger = logging.getLogger(__name__)


def _send_email_base(to_email: str, subject: str, html_body: str) -> dict:
    """
    Send an HTML email using Brevo API.
    """

    print("\n" + "=" * 55)
    print("  AS PLANTS EMAIL SEND ATTEMPT")
    print("=" * 55)
    print(f"  To      : {to_email}")
    print(f"  Subject : {subject}")

    # Brevo API key from Render Environment Variables
    api_key = os.getenv("BREVO_API_KEY", "")

    # We use SMTP_USERNAME as the verified Brevo sender email
    sender_email = settings.SMTP_SENDER

    print(f"  Sender  : {sender_email}")
    print(f"  Brevo API Key: {'SET' if api_key else 'NOT SET'}")
    print("=" * 55)

    # Check Brevo API key
    if not api_key:
        msg = "BREVO_API_KEY is not set in Render Environment."
        print(f"[EMAIL] ERROR: {msg}")
        return {
            "success": False,
            "message": msg
        }

    # Check sender email
    if not sender_email:
        msg = "SMTP_USERNAME is not set. This is used as the Brevo sender email."
        print(f"[EMAIL] ERROR: {msg}")
        return {
            "success": False,
            "message": msg
        }

    # Brevo API request
    payload = {
        "sender": {
            "name": settings.SMTP_DISPLAY_NAME or "AS Plants",
            "email": sender_email
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_body
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        print("[EMAIL] Sending email through Brevo API...")

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=20
        )

        print(f"[EMAIL] Brevo response: {response.status_code}")

        if response.ok:
            print(f"[EMAIL] Email sent successfully to {to_email}")

            logger.info(
                f"Email sent successfully to {to_email}"
            )

            return {
                "success": True,
                "message": "Email sent successfully"
            }

        error_text = response.text

        print(f"[EMAIL] Brevo error: {error_text}")

        logger.error(
            f"Brevo API error ({response.status_code}): {error_text}"
        )

        return {
            "success": False,
            "message": f"Brevo API error ({response.status_code}): {error_text}"
        }

    except Exception as e:
        err_msg = (
            f"Failed to send email: "
            f"{type(e).__name__}: {e}"
        )

        print(f"[EMAIL] ERROR: {err_msg}")
        print(traceback.format_exc())

        logger.error(err_msg)

        return {
            "success": False,
            "message": err_msg
        }


def send_otp_email(to_email: str, otp: str) -> dict:
    """
    Sends OTP verification email.
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

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0f7f3;padding:40px 0;">

    <tr>
      <td align="center">

        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">

              <p style="margin:0 0 6px;font-size:28px;font-weight:800;color:#ffffff;letter-spacing:1px;">
                &#127807; AS Plants
              </p>

              <p style="margin:0;font-size:13px;color:#a8d5b5;letter-spacing:0.5px;">
                Bring Nature Home
              </p>

            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 20px;">

              <p style="margin:0 0 8px;font-size:20px;font-weight:700;color:#1B3B2B;">
                Email Verification
              </p>

              <p style="margin:0 0 28px;font-size:14px;color:#6b7b72;line-height:1.6;">
                To securely create your AS Plants account, please use the following One-Time Password (OTP):
              </p>

              <!-- OTP Box -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center"
                      style="background:#f0f7f3;border:2px dashed #2E6B4F;border-radius:16px;padding:28px 0;">

                    <p style="margin:0;font-size:42px;font-weight:800;letter-spacing:12px;color:#1B3B2B;font-family:'Courier New',monospace;">
                      {otp}
                    </p>

                  </td>
                </tr>
              </table>

              <p style="margin:24px 0 0;font-size:13px;color:#6b7b72;text-align:center;">
                This code is valid for
                <strong style="color:#1B3B2B;">5 minutes</strong>.
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

    return _send_email_base(
        to_email,
        subject,
        html_body
    )


def send_welcome_email(to_email: str, name: str) -> dict:
    """
    Sends a welcome email after successful registration.
    """

    subject = "Welcome to AS Plants! &#127807;"

    html_body = f"""<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8"/>
</head>

<body style="margin:0;padding:0;background:#f0f7f3;font-family:'Segoe UI',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0f7f3;padding:40px 0;">

    <tr>
      <td align="center">

        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">

              <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">
                &#127807; AS Plants
              </p>

              <p style="margin:0;font-size:13px;color:#a8d5b5;">
                Bring Nature Home
              </p>

            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px;">

              <p style="margin:0 0 12px;font-size:20px;font-weight:700;color:#1B3B2B;">
                Welcome, {name}! &#127881;
              </p>

              <p style="font-size:14px;color:#6b7b72;line-height:1.7;">
                Your AS Plants account has been created successfully.<br/>
                You can now browse our premium plant catalog, place orders, and track deliveries.
              </p>

              <p style="font-size:14px;color:#2E6B4F;font-weight:600;">
                Happy Planting! &#127807;
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 40px 28px;text-align:center;">

              <p style="margin:0;font-size:11px;color:#c0ccc5;">
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

    return _send_email_base(
        to_email,
        subject,
        html_body
    )


def send_password_reset_email(to_email: str, token: str) -> dict:
    """
    Sends password reset code.
    """

    subject = "AS Plants Password Reset Request"

    html_body = f"""<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8"/>
</head>

<body style="margin:0;padding:0;background:#f0f7f3;font-family:'Segoe UI',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0f7f3;padding:40px 0;">

    <tr>
      <td align="center">

        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(27,59,43,0.10);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1B3B2B 0%,#2E6B4F 100%);padding:36px 40px 28px;text-align:center;">

              <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">
                &#127807; AS Plants
              </p>

            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px;">

              <p style="margin:0 0 12px;font-size:20px;font-weight:700;color:#1B3B2B;">
                Password Reset
              </p>

              <p style="font-size:14px;color:#6b7b72;line-height:1.7;">
                We received a request to reset your AS Plants password.
                Use this code:
              </p>

              <!-- Reset Code -->
              <table width="100%" cellpadding="0" cellspacing="0">

                <tr>
                  <td align="center"
                      style="background:#f0f7f3;border:2px dashed #2E6B4F;border-radius:16px;padding:24px 0;">

                    <p style="margin:0;font-size:36px;font-weight:800;letter-spacing:10px;color:#1B3B2B;font-family:'Courier New',monospace;">
                      {token}
                    </p>

                  </td>
                </tr>

              </table>

              <p style="font-size:13px;color:#6b7b72;text-align:center;margin-top:20px;">
                If you didn't request this, please ignore this email.
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 40px 28px;text-align:center;">

              <p style="margin:0;font-size:11px;color:#c0ccc5;">
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

    return _send_email_base(
        to_email,
        subject,
        html_body
    )