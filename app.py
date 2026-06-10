from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random
from mail import send_email

app = Flask(__name__)
app.secret_key = "atm_secret_key"


def get_db():
    conn = sqlite3.connect("atm.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():

    account_no = request.form["account_no"]
    pin = request.form["pin"]

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE account_no=?",
        (account_no,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["pin"], pin):

        session["account_no"] = user["account_no"]
        session["name"] = user["name"]

        return redirect("/dashboard")

    return render_template(
        "login.html",
        msg="Invalid Account Number or PIN"
    )


@app.route("/dashboard")
def dashboard():

    if "account_no" not in session:
        return redirect("/")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE account_no=?",
        (session["account_no"],)
    ).fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user
    )

@app.route("/deposit", methods=["GET", "POST"])
def deposit():

    if "account_no" not in session:
        return redirect("/")

    if request.method == "POST":

        amount = float(request.form["amount"])

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        session["deposit_amount"] = amount

        conn.close()

        return redirect("/deposit_pin")

    return render_template("deposit.html")

@app.route("/withdrawal", methods=["GET", "POST"])
def withdrawal():

    if "account_no" not in session:
        return redirect("/")

    if request.method == "POST":

        amount = float(request.form["amount"])

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        current_balance = user["balance"]

        if amount > current_balance:

            conn.close()

            return render_template("notification.html", msg="Insufficient Balance")

        session["withdraw_amount"] = amount

        conn.close()

        return redirect("/withdrawal_pin")

    return render_template("withdrawal.html")

@app.route("/transactions")
def transactions():

    if "account_no" not in session:
        return redirect("/")

    conn = get_db()

    records = conn.execute(
        """
        SELECT *
        FROM transactions
        WHERE account_no=?
        ORDER BY id DESC
        """,
        (session["account_no"],)
    ).fetchall()

    conn.close()

    return render_template(
        "transactions.html",
        records=records
    )

@app.route("/update_pin", methods=["GET", "POST"])
def update_pin():

    if "account_no" not in session:
        return redirect("/")

    if request.method == "POST":

        current_pin = request.form["current_pin"]
        new_pin = request.form["new_pin"]
        confirm_pin = request.form["confirm_pin"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        if not check_password_hash(user["pin"],current_pin):

            conn.close()

            return render_template(
                "update_pin.html",
                msg="Current PIN is incorrect"
            )

        if new_pin != confirm_pin:

            conn.close()

            return render_template(
                "update_pin.html",
                msg="New PIN and Confirm PIN do not match"
            )

        if len(new_pin) != 4 or not new_pin.isdigit():

            conn.close()

            return render_template(
                "update_pin.html",
                msg="PIN must be exactly 4 digits"
            )
        hashed_pin = generate_password_hash(new_pin)

        conn.execute(
            "UPDATE users SET pin=? WHERE account_no=?",
            (hashed_pin, session["account_no"])
        )

        conn.commit()
        send_email(user["email"],  "PIN Changed","Your ATM PIN has been changed successfully.")
        conn.close()

        session.clear()

        return render_template("notification.html",
        msg="PIN Updated Successfully. Please login again with your new PIN."
    )

    return render_template("update_pin.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username=?",
            (username,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):
            session["admin"] = username
            return redirect("/admin_dashboard")

        return render_template(
            "admin_login.html",
            msg="Invalid Credentials"
        )

    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    total_transactions = conn.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    result = conn.execute(
        "SELECT SUM(balance) FROM users"
    ).fetchone()

    total_balance = result[0] if result[0] else 0

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_transactions=total_transactions,
        total_balance=total_balance
    )

@app.route("/add_user", methods=["GET", "POST"])
def add_user():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        account_no = request.form["account_no"]
        name = request.form["name"]
        email = request.form["email"]
        pin = request.form["pin"]
        balance = float(request.form["balance"])

        hashed_pin = generate_password_hash(pin)

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (account_no,name,email,pin,balance)
                VALUES
                (?,?,?,?,?)
                """,
                (
                    account_no,
                    name,
                    email,
                    hashed_pin,
                    balance
                )
            )

            conn.commit()

            conn.close()

            return render_template(
                "notification.html",
                msg="User Created Successfully"
            )

        except Exception as e:

            conn.close()

            return render_template(
                "add_user.html",
                msg="Account Number or Email already exists"
            )

    return render_template(
        "add_user.html"
    )

@app.route("/view_users")
def view_users():

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    users = conn.execute(
        """
        SELECT
        id,
        account_no,
        name,
        email,
        balance
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "view_users.html",
        users=users
    )

@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    conn.execute(
        "DELETE FROM users WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/view_users")

@app.route("/all_transactions")
def all_transactions():

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    records = conn.execute(
        """
        SELECT *
        FROM transactions
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "view_transactions.html",
        records=records
    )

@app.route("/forgot_pin", methods=["GET", "POST"])
def forgot_pin():

    if request.method == "POST":

        account_no = request.form["account_no"]
        email = request.form["email"]

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE account_no=? AND email=?
            """,
            (account_no, email)
        ).fetchone()

        conn.close()

        if user:

            otp = random.randint(100000, 999999)

            session["otp"] = str(otp)
            session["reset_account"] = account_no

            send_email(email, "ATM OTP Verification", f"Your OTP is: {otp}")

            return redirect("/verify_otp")

        return render_template(
            "forgot_pin.html",
            msg="Account Number and Email do not match"
        )

    return render_template(
        "forgot_pin.html"
    )

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        if entered_otp == session.get("otp"):

            return redirect("/reset_pin")

        return render_template(
            "verify_otp.html",
            msg="Invalid OTP"
        )

    return render_template(
        "verify_otp.html"
    )

@app.route("/reset_pin", methods=["GET", "POST"])
def reset_pin():

    if request.method == "POST":

        new_pin = request.form["new_pin"]

        if len(new_pin) != 4:

            return render_template(
                "reset_pin.html",
                msg="PIN must be 4 digits"
            )

        hashed_pin = generate_password_hash(
            new_pin
        )

        conn = get_db()

        conn.execute(
            """
            UPDATE users
            SET pin=?
            WHERE account_no=?
            """,
            (
                hashed_pin,
                session["reset_account"]
            )
        )

        conn.commit()
        conn.close()

        session.pop("otp", None)

        return render_template(
            "notification.html",
            msg="PIN Reset Successfully"
        )

    return render_template(
        "reset_pin.html"
    )

@app.route("/deposit_pin", methods=["GET","POST"])
def deposit_pin():

    if "account_no" not in session:
        return redirect("/")

    if request.method == "POST":

        pin = request.form["pin"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        if not check_password_hash(
            user["pin"],
            pin
        ):

            conn.close()

            return render_template(
                "deposit_pin.html",
                msg="Incorrect PIN"
            )

        amount = session["deposit_amount"]

        new_balance = user["balance"] + amount

        conn.execute(
            "UPDATE users SET balance=? WHERE account_no=?",
            (
                new_balance,
                session["account_no"]
            )
        )

        conn.execute(
            """
            INSERT INTO transactions
            (
            account_no,
            transaction_type,
            amount,
            balance
            )
            VALUES
            (?,?,?,?)
            """,
            (
                session["account_no"],
                "Deposit",
                amount,
                new_balance
            )
        )

        conn.commit()
        conn.close()

        return render_template(
            "notification.html",
            msg=f"₹{amount} Deposited Successfully"
        )

    return render_template("deposit_pin.html")

@app.route("/withdrawal_pin", methods=["GET", "POST"])
def withdrawal_pin():

    if "account_no" not in session:
        return redirect("/")

    if request.method == "POST":

        pin = request.form["pin"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        if not check_password_hash(
            user["pin"],
            pin
        ):

            conn.close()

            return render_template(
                "withdrawal_pin.html",
                msg="Incorrect PIN"
            )

        amount = session["withdraw_amount"]

        if amount > user["balance"]:

            conn.close()

            return render_template(
                "withdrawal_pin.html",
                msg="Insufficient Balance"
            )

        new_balance = user["balance"] - amount

        conn.execute(
            "UPDATE users SET balance=? WHERE account_no=?",
            (
                new_balance,
                session["account_no"]
            )
        )

        conn.execute(
            """
            INSERT INTO transactions
            (
            account_no,
            transaction_type,
            amount,
            balance
            )
            VALUES
            (?,?,?,?)
            """,
            (
                session["account_no"],
                "Withdrawal",
                amount,
                new_balance
            )
        )

        conn.commit()

        send_email(
            user["email"],
            "Withdrawal Successful",
            f"₹{amount} withdrawn successfully.\nAvailable Balance: ₹{new_balance}"
        )

        conn.close()

        session.pop("withdraw_amount", None)

        return render_template(
            "notification.html",
            msg=f"₹{amount} Withdrawn Successfully"
        )

    return render_template(
        "withdrawal_pin.html"
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")




if __name__ == "__main__":
    app.run(debug=True)