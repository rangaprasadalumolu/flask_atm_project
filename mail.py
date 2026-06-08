import smtplib
from email.mime.text import MIMEText
import os

EMAIL = os.environ.get("EMAIL_USER")
PASSWORD = os.environ.get("EMAIL_PASS")

def send_email(to_email, subject, body):

    msg = MIMEText(body)

    msg['Subject'] = subject
    msg['From'] = EMAIL
    msg['To'] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)

        server.starttls()

        server.login(EMAIL, PASSWORD)

        server.sendmail(EMAIL, to_email, msg.as_string())

        server.quit()

        print("Email sent successfully")

    except Exception as e:
        print("Email Error:", e)