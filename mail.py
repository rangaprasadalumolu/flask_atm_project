import smtplib
from email.mime.text import MIMEText
import os

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")

def send_email(to_email, subject, body):

    try:
        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)

        print("Email sent successfully")

    except Exception as e:
        print("===================================")
        print("EMAIL ERROR")
        print(str(e))
        print("To:", to_email)
        print("Subject:", subject)
        print("Body:", body)
        print("===================================")

        # Prevent application crash
        return False

    return True