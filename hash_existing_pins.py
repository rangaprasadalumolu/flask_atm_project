import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("atm.db")
cursor = conn.cursor()

cursor.execute("SELECT id,pin FROM users")

users = cursor.fetchall()

for user in users:

    user_id = user[0]
    old_pin = user[1]

    hashed_pin = generate_password_hash(old_pin)

    cursor.execute(
        "UPDATE users SET pin=? WHERE id=?",
        (hashed_pin, user_id)
    )

conn.commit()
conn.close()

print("All PINs Hashed Successfully")