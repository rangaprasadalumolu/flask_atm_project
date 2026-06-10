import sqlite3

conn = sqlite3.connect("atm.db")
cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM users WHERE email=?",
    ("prasad@gmail.com",)
)

existing = cursor.fetchone()

if existing:
    print("User already exists")
else:
    cursor.execute("""
    INSERT INTO users
    (account_no,name,email,pin,balance)
    VALUES
    (
    '123456789012',
    'Ranga Prasad',
    'prasad@gmail.com',
    '1234',
    5000
    )
    """)

    conn.commit()
    print("User Added Successfully")

conn.close()