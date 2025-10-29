import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_ADDRESS = os.environ.get("FROM_ADDRESS", SMTP_USER)

def send_email(
    to_addrs: List[str],
    subject: str,
    body: str,
    html: Optional[str] = None,
    attachments: Optional[List[str]] = None
) -> bool:
    """
    Send an email. attachments: list of file paths to attach.
    Returns True on success, raises exception on failure.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = ", ".join(to_addrs if isinstance(to_addrs, (list,tuple)) else [to_addrs])
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    # attachments
    for path in attachments or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            import mimetypes
            mime, _ = mimetypes.guess_type(path)
            if not mime:
                mime = "application/octet-stream"
            maintype, subtype = mime.split("/", 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.split("/")[-1])
        except Exception:
            # ignore single attachment failure but log upstream
            pass

    # send
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT in (587, 25):
            s.starttls()
            s.ehlo()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True
