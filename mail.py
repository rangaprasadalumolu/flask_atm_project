import smtplib
from email.mime.text import MIMEText

EMAIL = "rangaprasadalumolu66@gmail.com"
PASSWORD = "gwgxjkyimwwfwijs"

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