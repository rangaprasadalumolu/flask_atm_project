import sqlite3

DATABASE = "atm.db"

conn = sqlite3.connect(DATABASE)

cursor = conn.cursor()


# ==========================================================
# USERS TABLE
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    account_no TEXT UNIQUE NOT NULL,

    name TEXT NOT NULL,

    email TEXT UNIQUE NOT NULL,

    pin TEXT NOT NULL,

    balance REAL NOT NULL DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")


# ==========================================================
# TRANSACTIONS TABLE
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    account_no TEXT NOT NULL,

    transaction_type TEXT NOT NULL,

    amount REAL NOT NULL,

    balance REAL NOT NULL,

    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(account_no)

    REFERENCES users(account_no)

    ON DELETE CASCADE

)
""")


# ==========================================================
# ADMIN TABLE
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL

)
""")


conn.commit()

conn.close()

print("Database created successfully.")