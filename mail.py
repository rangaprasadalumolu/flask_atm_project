import smtplib
from email.mime.text import MIMEText

EMAIL = "your_email@gmail.com"
PASSWORD = "your_app_password"

def send_email(to_email, subject, body):

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