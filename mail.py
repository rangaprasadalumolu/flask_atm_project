import smtplib
from email.mime.text import MIMEText
import os

def send_email(to_email, subject, body):

    EMAIL = os.getenv("EMAIL_USER")
    PASSWORD = os.getenv("EMAIL_PASS")

    try:

        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                EMAIL,
                PASSWORD
            )

            server.send_message(msg)

        return True

    except Exception as e:

        print("EMAIL ERROR:")
        print(e)

        return False