from flask import Flask
from flask import session
import random
from mail import send_email
import sqlite3
import os
from dotenv import load_dotenv
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

conn = sqlite3.connect("atm.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT,
    account_no TEXT UNIQUE,
    pin TEXT,
    balance INTEGER DEFAULT 0
)
""")

conn.commit()

@app.route("/")
def home():
    return render_template("welcome.html")
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        if len(phone) != 10:
            return render_template("register.html", message="Phone number must be 10 digits")
        account_no = request.form["account_no"]
        pin = request.form["pin"]
        hashed_pin = generate_password_hash(pin)
        if len(pin) != 4:
            return render_template("register.html", message="PIN must be 4 digits")

        # Check account already exists

        cursor.execute(
            "SELECT * FROM users WHERE account_no=?",
            (account_no,)
        )

        existing = cursor.fetchone()

        if existing:
            return render_template(
                "register.html",
                message="Account already exists"
            )

        cursor.execute(
            """
            INSERT INTO users
            (name,email,phone,account_no,pin,balance)
            VALUES(?,?,?,?,?,?)
            """,
            (
                name,
                email,
                phone,
                account_no,
                hashed_pin,
                0
            )
        )

        conn.commit()

        return redirect(url_for("home"))

    return render_template(
        "register.html",
        message=""
    )
@app.route("/account", methods=["GET","POST"])
def account():

    if request.method == "POST":

        account_no = request.form["account_no"]

        cursor.execute(
            "SELECT * FROM users WHERE account_no=?",
            (account_no,)
        )

        user = cursor.fetchone()

        if user:

            session["account_no"] = account_no

            return render_template(
                "password.html",
                message=""
            )

        return render_template(
            "account_no.html",
            message="Account Not Found"
        )

    return render_template(
        "account_no.html",
        message=""
    )
@app.route("/pin", methods=["POST"])
def pin():

    pin = request.form["pin"]

    account_no = session.get("account_no")

    cursor.execute(
        """
        SELECT name,email
        FROM users
        WHERE account_no=? AND pin=?
        """,
        (account_no, pin)
    )

    user = cursor.fetchone()

    if user:

        name = user[0]
        email = user[1]

        session["name"] = name

        otp = str(random.randint(100000,999999))

        session["otp"] = otp

        send_email(
            email,
            "ATM Login OTP",
            f"Your OTP is {otp}"
        )

        return render_template(
            "otp.html",
            message="OTP Sent Successfully"
        )

    return render_template(
        "password.html",
        message="Wrong PIN"
    )
@app.route("/verify_otp", methods=["POST"])
def verify_otp():

    entered_otp = request.form["otp"]

    actual_otp = session.get("otp")

    if entered_otp == actual_otp:

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "otp.html",
        message="Invalid OTP"
    )
@app.route("/dashboard")
def dashboard():

    if "account_no" not in session:
        return redirect(url_for("account"))

    return render_template(
        "homepage.html",
        name=session.get("name")
    )
@app.route("/check_balance")
def check_balance():

    if "account_no" not in session:
        return redirect(url_for("account"))

    account_no = session.get("account_no")

    cursor.execute(
        """
        SELECT name,balance
        FROM users
        WHERE account_no=?
        """,
        (account_no,)
    )

    user = cursor.fetchone()

    return render_template(
        "check_balance.html",
        name=user[0],
        balance=user[1],
        account_no=account_no
    )
@app.route("/deposit", methods=["GET","POST"])
def deposit():

    if "account_no" not in session:
        return redirect(url_for("account"))

    if request.method == "POST":

        amount = int(request.form["amount"])

        if amount <= 0:
            return render_template(
                "deposit.html",
                message="Invalid Amount"
            )

        session["deposit_amount"] = amount

        return render_template(
            "deposit_pin.html"
        )

    return render_template(
        "deposit.html",
        message=""
    )
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_no TEXT,
    type TEXT,
    amount INTEGER,
    balance INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

@app.route("/confirm_deposit", methods=["POST"])
def confirm_deposit():

    pin = request.form["pin"]

    account_no = session.get("account_no")

    amount = session.get("deposit_amount")

    cursor.execute(
        """
        SELECT pin,balance,email
        FROM users
        WHERE account_no=?
        """,
        (account_no,)
    )

    user = cursor.fetchone()

    if not user:
        return redirect(url_for("account"))

    db_pin = user[0]
    balance = user[1]
    email = user[2]

    if not check_password_hash(db_pin, pin):

        return render_template(
            "deposit.html",
            message="Wrong PIN"
        )

    new_balance = balance + amount

    cursor.execute(
        """
        UPDATE users
        SET balance=?
        WHERE account_no=?
        """,
        (
            new_balance,
            account_no
        )
    )

    conn.commit()

    cursor.execute(
        """
        INSERT INTO transactions
        (account_no,type,amount,balance)
        VALUES(?,?,?,?)
        """,
        (
            account_no,
            "Deposit",
            amount,
            new_balance
        )
    )

    conn.commit()

    send_email(
        email,
        "Deposit Successful",
        f"""
Amount Deposited: ₹{amount}

Current Balance: ₹{new_balance}
"""
    )

    return render_template(
        "deposit.html",
        message=f"₹{amount} Deposited Successfully"
    )
@app.route("/withdraw", methods=["GET","POST"])
def withdraw():

    if "account_no" not in session:
        return redirect(url_for("account"))

    if request.method == "POST":

        amount = int(request.form["amount"])

        if amount <= 0:

            return render_template(
                "withdraw.html",
                message="Invalid Amount"
            )

        session["withdraw_amount"] = amount

        return render_template(
            "withdraw_pin.html"
        )

    return render_template(
        "withdraw.html",
        message=""
    )
@app.route("/confirm_withdraw", methods=["POST"])
def confirm_withdraw():

    pin = request.form["pin"]

    account_no = session.get("account_no")

    amount = session.get("withdraw_amount")

    cursor.execute(
        """
        SELECT pin,balance,email
        FROM users
        WHERE account_no=?
        """,
        (account_no,)
    )

    user = cursor.fetchone()

    if not user:
        return redirect(url_for("account"))

    db_pin = user[0]
    balance = user[1]
    email = user[2]

    if not check_password_hash(db_pin, pin):

        return render_template(
            "withdraw.html",
            message="Wrong PIN"
        )

    if amount > balance:

        return render_template(
            "withdraw.html",
            message="Insufficient Balance"
        )

    new_balance = balance - amount

    cursor.execute(
        """
        UPDATE users
        SET balance=?
        WHERE account_no=?
        """,
        (
            new_balance,
            account_no
        )
    )

    conn.commit()

    cursor.execute(
        """
        INSERT INTO transactions
        (account_no,type,amount,balance)
        VALUES(?,?,?,?)
        """,
        (
            account_no,
            "Withdraw",
            amount,
            new_balance
        )
    )

    conn.commit()

    send_email(
        email,
        "Withdrawal Successful",
        f"""
Amount Withdrawn: ₹{amount}

Remaining Balance: ₹{new_balance}
"""
    )

    return render_template(
        "withdraw.html",
        message=f"₹{amount} Withdrawn Successfully"
    )
@app.route("/transactions")
def transactions():

    if "account_no" not in session:
        return redirect(url_for("account"))

    account_no = session.get("account_no")

    cursor.execute(
        """
        SELECT date,type,amount,balance
        FROM transactions
        WHERE account_no=?
        ORDER BY date DESC
        """,
        (account_no,)
    )

    data = cursor.fetchall()

    return render_template(
        "transaction.html",
        transactions=data
    )
@app.route("/update_pin", methods=["GET","POST"])
def update_pin():

    if "account_no" not in session:
        return redirect(url_for("account"))

    if request.method == "POST":

        old_pin = request.form["old_pin"]
        new_pin = request.form["new_pin"]
        confirm_pin = request.form["confirm_pin"]

        account_no = session.get("account_no")

        cursor.execute(
            """
            SELECT pin,email
            FROM users
            WHERE account_no=?
            """,
            (account_no,)
        )

        user = cursor.fetchone()

        current_pin = user[0]
        email = user[1]

        if not check_password_hash(current_pin, old_pin):

            return render_template(
                "update_pin.html",
                message="Current PIN is incorrect"
            )

        if not check_password_hash(new_pin, confirm_pin):

            return render_template(
                "update_pin.html",
                message="New PIN and Confirm PIN do not match"
            )

        if len(new_pin) != 4:

            return render_template(
                "update_pin.html",
                message="PIN must be 4 digits"
            )

        cursor.execute(
            """
            UPDATE users
            SET pin=?
            WHERE account_no=?
            """,
            (
                new_pin,
                account_no
            )
        )

        conn.commit()

        send_email(
            email,
            "ATM PIN Updated",
            "Your ATM PIN has been changed successfully."
        )

        return render_template(
            "update_pin.html",
            message="PIN Updated Successfully"
        )

    return render_template(
        "update_pin.html",
        message=""
    )
@app.route("/logout")
def logout():

    session.clear()

    return render_template("logout.html")
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)