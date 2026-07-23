import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("atm.db")

cursor = conn.cursor()

users = cursor.execute(
    "SELECT account_no,pin FROM users"
).fetchall()

for account_no, pin in users:

    if len(pin) == 4:

        cursor.execute(
            """
            UPDATE users
            SET pin=?
            WHERE account_no=?
            """,
            (
                generate_password_hash(pin),
                account_no
            )
        )

conn.commit()

conn.close()

print("Existing PINs hashed successfully.")