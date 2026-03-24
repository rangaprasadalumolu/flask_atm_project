from flask import Flask, render_template, request, session
import re
import mysql.connector
import random
from mail import send_email   # ✅ Import from separate file

app = Flask(__name__)
app.secret_key = "my secret key"

# ================= DATABASE =================
connect_db = mysql.connector.connect(
    host="localhost",
    user="yourusername",
    password="yourpassword",
    database="yourdatabasename"
)

cursor = connect_db.cursor()

# ================= ROUTES =================

@app.route("/")
def welcome():
    return render_template("welcome.html")


@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        account_no = request.form["account"]
        pattern = r'^1\d{3} \d{4} \d{6}$'

        if re.match(pattern, account_no):
            cursor.execute("select ac_no from users_data where ac_no=%s",(account_no,))
            res = cursor.fetchone()

            if res:
                session["ac_no"] = account_no
                return render_template("password.html",pass_msg="Account verified. Enter ATM PIN")
            else:
                return render_template("account_no.html",ac_no="Account number does not exist")
        else:
            return render_template("account_no.html",ac_no="Enter account number in format: 1XXX XXXX XXXXXXX")

    return render_template("account_no.html", ac_no="")

# ================= PIN + OTP =================

@app.route("/pin", methods=["GET", "POST"])
def pin():
    if request.method == "POST":
        pin = request.form["password"]
        ac_no = session.get("ac_no")

        cursor.execute("select name, email from users_data where ac_no=%s and pin=%s",(ac_no, pin))
        res = cursor.fetchone()

        if res:
            name = res[0]
            email = res[1]

            session["name"] = name

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            session["otp"] = otp

            send_email(email, "ATM Login OTP", f"Your OTP is {otp}")

            return render_template("otp.html")

        else:
            return render_template("password.html", pass_msg="Wrong PIN. Try again.")

    return render_template("password.html")


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    user_otp = request.form["otp"]

    if user_otp == session.get("otp"):
        return render_template("homepage.html", name=session.get("name"))
    else:
        return render_template("otp.html", message="Invalid OTP")

# ================= BALANCE =================

@app.route("/check_balance")
def check_balance():
    ac_no = session.get("ac_no")

    if ac_no:
        cursor.execute("select name, balance from users_data where ac_no=%s",(ac_no,))
        res = cursor.fetchone()

        if res:
            return render_template("check_balance.html", name=res[0], balance=res[1])

    return "Session expired. Please login again."


@app.route("/homepage")
def return_home():
    return render_template("homepage.html", name=session.get("name"))

# ================= DEPOSIT =================

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if request.method == "POST":
        amount = int(request.form["amount"])
        session["deposit_amount"] = amount
        return render_template("deposit_pin.html", message="")

    return render_template("deposit.html", message="")


@app.route("/confirm_deposit", methods=["POST"])
def confirm_deposit():
    pin = request.form["pin"]
    ac_no = session.get("ac_no")
    amount = session.get("deposit_amount")

    cursor.execute("select pin, balance, email from users_data where ac_no=%s", (ac_no,))
    res = cursor.fetchone()

    if res:
        db_pin = str(res[0])
        balance = res[1]
        email = res[2]

        if pin != db_pin:
            return render_template("deposit.html", message="Incorrect PIN")

        new_balance = balance + amount

        cursor.execute("update users_data set balance=%s where ac_no=%s",(new_balance, ac_no))
        connect_db.commit()

        cursor.execute("insert into transactions(ac_no,type,amount,balance) values(%s,%s,%s,%s)",
                       (ac_no, "Deposit", amount, new_balance))
        connect_db.commit()

        # EMAIL ALERT
        send_email(email, "Deposit Alert",
                   f"Rs {amount} deposited successfully.\nNew balance: Rs {new_balance}")

        return render_template("deposit.html", message="Deposit successful!")

    return render_template("deposit.html", message="Something went wrong")

# ================= WITHDRAW =================

@app.route("/withdraw", methods=["GET","POST"])
def withdraw():
    if request.method == "POST":
        amount = int(request.form["amount"])
        session["withdraw_amount"] = amount
        return render_template("withdraw_pin.html")

    return render_template("withdraw.html", message="")


@app.route("/confirm_withdraw", methods=["POST"])
def confirm_withdraw():
    pin = request.form["pin"]
    ac_no = session.get("ac_no")
    amount = session.get("withdraw_amount")

    cursor.execute("select pin, balance, email from users_data where ac_no=%s",(ac_no,))
    res = cursor.fetchone()

    if res:
        db_pin = str(res[0])
        balance = res[1]
        email = res[2]

        if pin != db_pin:
            return render_template("withdraw.html", message="Incorrect PIN")

        if amount > balance:
            return render_template("withdraw.html", message="Insufficient balance")

        new_balance = balance - amount

        cursor.execute("update users_data set balance=%s where ac_no=%s",(new_balance, ac_no))
        connect_db.commit()

        cursor.execute("insert into transactions(ac_no,type,amount,balance) values(%s,%s,%s,%s)",
                       (ac_no, "Withdraw", amount, new_balance))
        connect_db.commit()

        # EMAIL ALERT
        send_email(email, "Withdrawal Alert",
                   f"Rs {amount} withdrawn.\nRemaining balance: Rs {new_balance}")

        return render_template("withdraw.html",
                               message=f"Withdrawal successful! Remaining balance: Rs{new_balance}")

# ================= TRANSACTION =================

@app.route("/transaction")
def transaction():
    ac_no = session.get("ac_no")
    cursor.execute("select date, type, amount, balance from transactions where ac_no=%s order by date desc",(ac_no,))
    data = cursor.fetchall()
    return render_template("transaction.html",transactions=data)

# ================= PIN UPDATE =================

@app.route("/update_pin", methods=["GET","POST"])
def update_pin():
    if request.method == "POST":
        old_pin = request.form["old_pin"]
        new_pin = request.form["new_pin"]
        confirm_pin = request.form["confirm_pin"]

        ac_no = session.get("ac_no")

        cursor.execute("select pin, email from users_data where ac_no=%s",(ac_no,))
        res = cursor.fetchone()

        if res:
            current_pin = str(res[0])
            email = res[1]

            if old_pin != current_pin:
                return render_template("update_pin.html", message="Current PIN is incorrect")

            if new_pin != confirm_pin:
                return render_template("update_pin.html", message="PIN mismatch")

            cursor.execute("update users_data set pin=%s where ac_no=%s", (new_pin, ac_no))
            connect_db.commit()

            # EMAIL ALERT
            send_email(email, "PIN Changed",
                       "Your ATM PIN has been successfully updated.")

            return render_template("update_pin.html", message="PIN updated successfully!")

    return render_template("update_pin.html", message="")

# ================= LOGOUT =================

@app.route("/cancel")
def cancel():
    session.clear()
    return render_template("logout.html")

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)