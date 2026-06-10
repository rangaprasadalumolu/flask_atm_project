import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("atm.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM admins")

cursor.execute(
    """
    INSERT INTO admins(username,password)
    VALUES(?,?)
    """,
    (
        "admin",
        generate_password_hash("admin123")
    )
)

conn.commit()
conn.close()

print("Admin Created Successfully")