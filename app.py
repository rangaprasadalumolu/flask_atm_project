from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import sqlite3
import random
import time
import re
from functools import wraps
import os

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from mail import send_email


# ==========================================================
# Flask Configuration
# ==========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)

DATABASE = "atm.db"

OTP_EXPIRY = 300          # 5 Minutes

MIN_PIN_LENGTH = 4

MAX_PIN_LENGTH = 4


# ==========================================================
# Database Connection
# ==========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================================
# Login Required Decorator
# ==========================================================

def login_required(function):

    @wraps(function)

    def wrapper(*args, **kwargs):

        if "account_no" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================================
# Admin Login Required
# ==========================================================

def admin_required(function):

    @wraps(function)

    def wrapper(*args, **kwargs):

        if "admin" not in session:

            flash(
                "Admin login required.",
                "warning"
            )

            return redirect(url_for("admin"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================================
# Validation Functions
# ==========================================================

def valid_email(email):

    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

    return re.match(pattern, email)


def valid_pin(pin):

    if len(pin) != 4:

        return False

    return pin.isdigit()


def valid_amount(amount):

    try:

        value = float(amount)

        return value > 0

    except:

        return False


# ==========================================================
# User Lookup Functions
# ==========================================================

def get_user(account_no):

    conn = get_db()

    user = conn.execute(

        """
        SELECT *
        FROM users
        WHERE account_no=?
        """,

        (account_no,)

    ).fetchone()

    conn.close()

    return user


def email_exists(email):

    conn = get_db()

    row = conn.execute(

        """
        SELECT id
        FROM users
        WHERE email=?
        """,

        (email,)

    ).fetchone()

    conn.close()

    return row is not None


def account_exists(account):

    conn = get_db()

    row = conn.execute(

        """
        SELECT id
        FROM users
        WHERE account_no=?
        """,

        (account,)

    ).fetchone()

    conn.close()

    return row is not None


# ==========================================================
# OTP Functions
# ==========================================================

def generate_otp():

    return str(

        random.randint(

            100000,

            999999

        )

    )


def save_otp(account_no, otp):

    session["otp"] = otp

    session["otp_account"] = account_no

    session["otp_time"] = int(

        time.time()

    )


def otp_expired():

    if "otp_time" not in session:

        return True

    current = int(time.time())

    return (

        current -

        session["otp_time"]

    ) > OTP_EXPIRY


def clear_otp():

    session.pop(

        "otp",

        None

    )

    session.pop(

        "otp_account",

        None

    )

    session.pop(

        "otp_time",

        None

    )


# ==========================================================
# Transaction Function
# ==========================================================

def add_transaction(

    account_no,

    transaction_type,

    amount,

    balance

):

    conn = get_db()

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

            account_no,

            transaction_type,

            amount,

            balance

        )

    )

    conn.commit()

    conn.close()


# ==========================================================
# Email Helper
# ==========================================================

def send_transaction_email(

    email,

    subject,

    body

):

    try:

        send_email(

            email,

            subject,

            body

        )

    except:

        pass


# ==========================================================
# Error Pages
# ==========================================================

@app.errorhandler(404)

def page_not_found(error):

    return render_template(

        "notification.html",

        msg="Page Not Found."

    ),404


@app.errorhandler(500)

def internal_error(error):

    return render_template(

        "notification.html",

        msg="Something went wrong."

    ),500

# ==========================================================
# LOGIN PAGE
# ==========================================================

@app.route("/")
def login():

    if "account_no" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ==========================================================
# USER LOGIN
# ==========================================================

@app.route("/login", methods=["POST"])
def login_post():

    account_no = request.form.get("account_no", "").strip()
    pin = request.form.get("pin", "").strip()

    if not account_no or not pin:
        flash("Please enter Account Number and PIN.", "danger")
        return redirect(url_for("login"))

    user = get_user(account_no)

    if user is None:

        flash("Account does not exist.", "danger")
        return redirect(url_for("login"))

    if not check_password_hash(user["pin"], pin):

        flash("Invalid PIN.", "danger")
        return redirect(url_for("login"))

    session.clear()

    session["account_no"] = user["account_no"]
    session["name"] = user["name"]

    flash(
        f"Welcome {user['name']}!",
        "success"
    )

    return redirect(url_for("dashboard"))


# ==========================================================
# USER REGISTRATION
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    account_no = request.form.get("account_no", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    pin = request.form.get("pin", "").strip()
    confirm_pin = request.form.get("confirm_pin", "").strip()

    # ---------- Validation ----------

    if not account_no:

        flash("Account Number is required.", "danger")
        return redirect(url_for("register"))

    if not name:

        flash("Full Name is required.", "danger")
        return redirect(url_for("register"))

    if not valid_email(email):

        flash("Enter a valid Email Address.", "danger")
        return redirect(url_for("register"))

    if account_exists(account_no):

        flash("Account Number already exists.", "danger")
        return redirect(url_for("register"))

    if email_exists(email):

        flash("Email is already registered.", "danger")
        return redirect(url_for("register"))

    if not valid_pin(pin):

        flash("PIN must be exactly 4 digits.", "danger")
        return redirect(url_for("register"))

    if pin != confirm_pin:

        flash("PIN and Confirm PIN do not match.", "danger")
        return redirect(url_for("register"))

    hashed_pin = generate_password_hash(pin)

    conn = get_db()

    conn.execute(
        """
        INSERT INTO users
        (
            account_no,
            name,
            email,
            pin,
            balance
        )

        VALUES

        (?,?,?,?,?)
        """,

        (
            account_no,
            name,
            email,
            hashed_pin,
            0
        )
    )

    conn.commit()
    conn.close()

    # Welcome Email

    send_transaction_email(

        email,

        "Welcome to ATM Management System",

        f"""
Hello {name},

Your account has been created successfully.

Account Number : {account_no}

Thank you for registering.

ATM Management System
"""
    )

    flash(

        "Registration Successful. Please Login.",

        "success"

    )

    return redirect(url_for("login"))


# ==========================================================
# USER LOGOUT
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(

        "Logged out successfully.",

        "success"

    )

    return redirect(url_for("login"))
# ==========================================================
# USER DASHBOARD
# ==========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = get_user(session["account_no"])

    conn = get_db()

    recent_transactions = conn.execute(
        """
        SELECT *
        FROM transactions
        WHERE account_no=?
        ORDER BY id DESC
        LIMIT 5
        """,
        (session["account_no"],)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        recent_transactions=recent_transactions
    )


# ==========================================================
# DEPOSIT
# ==========================================================

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    if request.method == "GET":
        return render_template("deposit.html")

    amount = request.form.get("amount", "").strip()

    if not valid_amount(amount):

        flash(
            "Enter a valid amount.",
            "danger"
        )

        return redirect(url_for("deposit"))

    session["deposit_amount"] = float(amount)

    return redirect(
        url_for("deposit_pin")
    )


# ==========================================================
# VERIFY PIN FOR DEPOSIT
# ==========================================================

@app.route("/deposit_pin", methods=["GET", "POST"])
@login_required
def deposit_pin():

    if "deposit_amount" not in session:

        flash(
            "Deposit session expired.",
            "warning"
        )

        return redirect(
            url_for("deposit")
        )

    if request.method == "GET":

        return render_template(
            "deposit_pin.html"
        )

    pin = request.form.get("pin", "").strip()

    user = get_user(
        session["account_no"]
    )

    if not check_password_hash(
        user["pin"],
        pin
    ):

        flash(
            "Incorrect PIN.",
            "danger"
        )

        return redirect(
            url_for("deposit_pin")
        )

    amount = session["deposit_amount"]

    new_balance = user["balance"] + amount

    conn = get_db()

    conn.execute(
        """
        UPDATE users
        SET balance=?
        WHERE account_no=?
        """,
        (
            new_balance,
            session["account_no"]
        )
    )

    conn.commit()
    conn.close()

    add_transaction(
        session["account_no"],
        "Deposit",
        amount,
        new_balance
    )

    send_transaction_email(
        user["email"],
        "Deposit Successful",
        f"""
₹{amount:.2f} has been deposited successfully.

Available Balance:
₹{new_balance:.2f}

Thank you.
"""
    )

    session.pop(
        "deposit_amount",
        None
    )

    flash(
        f"₹{amount:.2f} deposited successfully.",
        "success"
    )

    return redirect(
        url_for("dashboard")
    )


# ==========================================================
# WITHDRAW MONEY
# ==========================================================

@app.route("/withdrawal", methods=["GET", "POST"])
@login_required
def withdrawal():

    if request.method == "GET":

        return render_template(
            "withdrawal.html"
        )

    amount = request.form.get("amount", "").strip()

    if not valid_amount(amount):

        flash(
            "Enter a valid amount.",
            "danger"
        )

        return redirect(
            url_for("withdrawal")
        )

    amount = float(amount)

    user = get_user(
        session["account_no"]
    )

    if amount > user["balance"]:

        flash(
            "Insufficient balance.",
            "danger"
        )

        return redirect(
            url_for("withdrawal")
        )

    session["withdraw_amount"] = amount

    return redirect(
        url_for("withdrawal_pin")
    )


# ==========================================================
# VERIFY PIN FOR WITHDRAWAL
# ==========================================================

@app.route("/withdrawal_pin", methods=["GET", "POST"])
@login_required
def withdrawal_pin():

    if "withdraw_amount" not in session:

        flash(
            "Withdrawal session expired.",
            "warning"
        )

        return redirect(
            url_for("withdrawal")
        )

    if request.method == "GET":

        return render_template(
            "withdrawal_pin.html"
        )

    pin = request.form.get("pin", "").strip()

    user = get_user(
        session["account_no"]
    )

    if not check_password_hash(
        user["pin"],
        pin
    ):

        flash(
            "Incorrect PIN.",
            "danger"
        )

        return redirect(
            url_for("withdrawal_pin")
        )

    amount = session["withdraw_amount"]

    if amount > user["balance"]:

        session.pop(
            "withdraw_amount",
            None
        )

        flash(
            "Insufficient balance.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )

    new_balance = user["balance"] - amount

    conn = get_db()

    conn.execute(
        """
        UPDATE users
        SET balance=?
        WHERE account_no=?
        """,
        (
            new_balance,
            session["account_no"]
        )
    )

    conn.commit()
    conn.close()

    add_transaction(
        session["account_no"],
        "Withdrawal",
        amount,
        new_balance
    )

    send_transaction_email(
        user["email"],
        "Withdrawal Successful",
        f"""
₹{amount:.2f} has been withdrawn successfully.

Remaining Balance:
₹{new_balance:.2f}
"""
    )

    session.pop(
        "withdraw_amount",
        None
    )

    flash(
        f"₹{amount:.2f} withdrawn successfully.",
        "success"
    )

    return redirect(
        url_for("dashboard")
    )
# ==========================================================
# TRANSACTION HISTORY
# ==========================================================

@app.route("/transactions")
@login_required
def transactions():

    conn = get_db()

    records = conn.execute(
        """
        SELECT *
        FROM transactions
        WHERE account_no=?
        ORDER BY transaction_date DESC,id DESC
        """,
        (session["account_no"],)
    ).fetchall()

    conn.close()

    return render_template(
        "transactions.html",
        records=records
    )


# ==========================================================
# CHANGE PIN
# ==========================================================

@app.route("/update_pin", methods=["GET", "POST"])
@login_required
def update_pin():

    user = get_user(session["account_no"])

    if request.method == "GET":
        return render_template("update_pin.html")

    current_pin = request.form.get("current_pin", "").strip()
    new_pin = request.form.get("new_pin", "").strip()
    confirm_pin = request.form.get("confirm_pin", "").strip()

    if not check_password_hash(user["pin"], current_pin):

        flash(
            "Current PIN is incorrect.",
            "danger"
        )

        return redirect(url_for("update_pin"))

    if not valid_pin(new_pin):

        flash(
            "PIN must contain exactly 4 digits.",
            "danger"
        )

        return redirect(url_for("update_pin"))

    if new_pin != confirm_pin:

        flash(
            "New PIN and Confirm PIN do not match.",
            "danger"
        )

        return redirect(url_for("update_pin"))

    hashed_pin = generate_password_hash(new_pin)

    conn = get_db()

    conn.execute(
        """
        UPDATE users
        SET pin=?
        WHERE account_no=?
        """,
        (
            hashed_pin,
            session["account_no"]
        )
    )

    conn.commit()
    conn.close()

    send_transaction_email(
        user["email"],
        "PIN Changed Successfully",
        """
Your ATM PIN has been changed successfully.

If you did not perform this action,
please contact the administrator immediately.
"""
    )

    session.clear()

    flash(
        "PIN updated successfully. Please login again.",
        "success"
    )

    return redirect(url_for("login"))


# ==========================================================
# FORGOT PIN
# ==========================================================

@app.route("/forgot_pin", methods=["GET", "POST"])
def forgot_pin():

    if request.method == "GET":
        return render_template("forgot_pin.html")

    account_no = request.form.get("account_no", "").strip()
    email = request.form.get("email", "").strip().lower()

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE account_no=? AND email=?
        """,
        (
            account_no,
            email
        )
    ).fetchone()

    conn.close()

    if user is None:

        flash(
            "Account Number and Email do not match.",
            "danger"
        )

        return redirect(url_for("forgot_pin"))

    otp = generate_otp()

    save_otp(
        account_no,
        otp
    )

    send_transaction_email(
        email,
        "ATM OTP Verification",
        f"""
Your OTP is : {otp}

This OTP will expire in 5 minutes.
"""
    )

    flash(
        "OTP has been sent to your email.",
        "success"
    )

    return redirect(url_for("verify_otp"))


# ==========================================================
# VERIFY OTP
# ==========================================================

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "GET":
        return render_template("verify_otp.html")

    entered_otp = request.form.get("otp", "").strip()

    if otp_expired():

        clear_otp()

        flash(
            "OTP expired. Please request a new OTP.",
            "warning"
        )

        return redirect(url_for("forgot_pin"))

    if entered_otp != session.get("otp"):

        flash(
            "Invalid OTP.",
            "danger"
        )

        return redirect(url_for("verify_otp"))

    session["otp_verified"] = True

    flash(
        "OTP verified successfully.",
        "success"
    )

    return redirect(url_for("reset_pin"))


# ==========================================================
# RESET PIN
# ==========================================================

@app.route("/reset_pin", methods=["GET", "POST"])
def reset_pin():

    if not session.get("otp_verified"):

        flash(
            "Please verify OTP first.",
            "warning"
        )

        return redirect(url_for("forgot_pin"))

    if request.method == "GET":
        return render_template("reset_pin.html")

    new_pin = request.form.get("new_pin", "").strip()
    confirm_pin = request.form.get("confirm_pin", "").strip()

    if not valid_pin(new_pin):

        flash(
            "PIN must contain exactly 4 digits.",
            "danger"
        )

        return redirect(url_for("reset_pin"))

    if new_pin != confirm_pin:

        flash(
            "PINs do not match.",
            "danger"
        )

        return redirect(url_for("reset_pin"))

    hashed_pin = generate_password_hash(new_pin)

    conn = get_db()

    user = conn.execute(
        """
        SELECT email
        FROM users
        WHERE account_no=?
        """,
        (session["otp_account"],)
    ).fetchone()

    conn.execute(
        """
        UPDATE users
        SET pin=?
        WHERE account_no=?
        """,
        (
            hashed_pin,
            session["otp_account"]
        )
    )

    conn.commit()
    conn.close()

    send_transaction_email(
        user["email"],
        "PIN Reset Successful",
        """
Your ATM PIN has been reset successfully.

If you did not perform this action,
please contact support immediately.
"""
    )

    clear_otp()

    session.pop("otp_verified", None)

    flash(
        "PIN reset successful. Please login.",
        "success"
    )

    return redirect(url_for("login"))
# ==========================================================
# ADMIN LOGIN
# ==========================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = get_db()

    admin = conn.execute(
        """
        SELECT *
        FROM admin
        WHERE username=?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if admin is None:

        flash("Invalid Username.", "danger")

        return redirect(url_for("admin"))

    if not check_password_hash(admin["password"], password):

        flash("Invalid Password.", "danger")

        return redirect(url_for("admin"))

    session.clear()

    session["admin"] = username

    flash("Welcome Admin.", "success")

    return redirect(url_for("admin_dashboard"))


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():

    conn = get_db()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    total_transactions = conn.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    total_balance = conn.execute(
        """
        SELECT IFNULL(SUM(balance),0)
        FROM users
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_transactions=total_transactions,
        total_balance=total_balance
    )


# ==========================================================
# ADD USER
# ==========================================================

@app.route("/add_user", methods=["GET", "POST"])
@admin_required
def add_user():

    if request.method == "GET":
        return render_template("add_user.html")

    account_no = request.form["account_no"].strip()
    name = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    pin = request.form["pin"].strip()
    balance = request.form["balance"].strip()

    if account_exists(account_no):

        flash("Account already exists.", "danger")

        return redirect(url_for("add_user"))

    if email_exists(email):

        flash("Email already exists.", "danger")

        return redirect(url_for("add_user"))

    if not valid_pin(pin):

        flash("PIN must contain exactly 4 digits.", "danger")

        return redirect(url_for("add_user"))

    if not valid_amount(balance):

        flash("Invalid balance.", "danger")

        return redirect(url_for("add_user"))

    conn = get_db()

    conn.execute(
        """
        INSERT INTO users
        (
            account_no,
            name,
            email,
            pin,
            balance
        )

        VALUES
        (?,?,?,?,?)
        """,

        (
            account_no,
            name,
            email,
            generate_password_hash(pin),
            float(balance)
        )
    )

    conn.commit()
    conn.close()

    flash("User added successfully.", "success")

    return redirect(url_for("view_users"))


# ==========================================================
# VIEW USERS
# ==========================================================

@app.route("/view_users")
@admin_required
def view_users():

    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:

        users = conn.execute(
            """
            SELECT *
            FROM users
            WHERE
            account_no LIKE ?
            OR name LIKE ?
            OR email LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        users = conn.execute(
            """
            SELECT *
            FROM users
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "view_users.html",
        users=users,
        search=search
    )


# ==========================================================
# DELETE USER
# ==========================================================

@app.route("/delete_user/<account_no>")
@admin_required
def delete_user(account_no):

    conn = get_db()

    conn.execute(
        "DELETE FROM users WHERE account_no=?",
        (account_no,)
    )

    conn.execute(
        "DELETE FROM transactions WHERE account_no=?",
        (account_no,)
    )

    conn.commit()

    conn.close()

    flash("User deleted successfully.", "success")

    return redirect(url_for("view_users"))


# ==========================================================
# VIEW TRANSACTIONS
# ==========================================================

@app.route("/view_transactions")
@admin_required
def view_transactions():

    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:

        records = conn.execute(
            """
            SELECT *
            FROM transactions
            WHERE account_no LIKE ?
            ORDER BY transaction_date DESC,id DESC
            """,
            (f"%{search}%",)
        ).fetchall()

    else:

        records = conn.execute(
            """
            SELECT *
            FROM transactions
            ORDER BY transaction_date DESC,id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "view_transactions.html",
        records=records,
        search=search
    )


# ==========================================================
# ADMIN LOGOUT
# ==========================================================

@app.route("/admin_logout")
def admin_logout():

    session.clear()

    flash("Admin logged out successfully.", "success")

    return redirect(url_for("admin"))


# ==========================================================
# APPLICATION START
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )