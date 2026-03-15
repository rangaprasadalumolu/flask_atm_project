from flask import Flask, render_template, request, session
import re
import mysql.connector

app = Flask(__name__)
app.secret_key = "my secret key"

connect_db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="atm"
)

cursor = connect_db.cursor()

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

@app.route("/pin", methods=["GET", "POST"])
def pin():
    if request.method == "POST":
        pin = request.form["password"]
        ac_no = session.get("ac_no")
        cursor.execute("select name from users_data where ac_no=%s and pin=%s",(ac_no, pin))
        res = cursor.fetchone()
        if res:
            name = res[0]
            return render_template("homepage.html", name=name)
        else:
            return render_template("password.html",pass_msg="Wrong PIN. Try again.")

    return render_template("password.html")

@app.route("/check_balance")
def check_balance():
    ac_no = session.get("ac_no")
    if ac_no:
        cursor.execute("select name, balance from users_data where ac_no=%s",(ac_no,))
        res = cursor.fetchone()
        if res:
            name = res[0]
            balance = res[1]
            return render_template("check_balance.html", name=name, balance=balance)

    return "Session expired. Please login again."
@app.route("/homepage")
def return_home():
    return render_template("homepage.html")

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if request.method == "POST":
        amount = int(request.form["amount"])
        ac_no = session.get("ac_no")

        cursor.execute("update users_data set balance = balance + %s where ac_no = %s",(amount, ac_no))

        connect_db.commit()
        cursor.execute("select balance from users_data where ac_no=%s",(ac_no,))

        balance = cursor.fetchone()[0]

        cursor.execute("insert into transactions(ac_no,type,amount,balance) values(%s,%s,%s,%s)",(ac_no,"Deposit",amount,balance))

        connect_db.commit()

        return render_template("deposit.html", message="Amount deposited successfully!")

    return render_template("deposit.html", message="")

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    if request.method == "POST":
        amount = int(request.form["amount"])
        ac_no = session.get("ac_no")

        # check current balance
        cursor.execute("select balance from users_data where ac_no=%s",(ac_no,))
        res = cursor.fetchone()

        if res:
            balance = res[0]
            if amount > balance:
                return render_template("withdraw.html", message="Insufficient balance!")
            else:
                cursor.execute("update users_data set balance = balance - %s WHERE ac_no=%s",(amount, ac_no))

                connect_db.commit()
                cursor.execute("insert into transactions(ac_no,type,amount,balance) values(%s,%s,%s,%s)",(ac_no,"Withdraw",amount,balance))

                connect_db.commit()

                return render_template("withdraw.html", message="Withdrawal successful!")

    return render_template("withdraw.html", message="")


@app.route("/transaction")
def transaction():
    ac_no = session.get("ac_no")
    cursor.execute("select date, type, amount, balance from transactions where ac_no=%s order by date desc",(ac_no,))
    data = cursor.fetchall()

    return render_template("transaction.html",transactions=data)


@app.route("/update_pin", methods=["GET","POST"])
def update_pin():
    if request.method == "POST":
        old_pin = request.form["old_pin"]
        new_pin = request.form["new_pin"]
        confirm_pin = request.form["confirm_pin"]

        ac_no = session.get("ac_no")

        # check current pin
        cursor.execute("select pin from users_data where ac_no=%s",(ac_no,))

        res = cursor.fetchone()

        if res:
            current_pin = str(res[0])
            if old_pin != current_pin:
                return render_template("update_pin.html", message="Current PIN is incorrect")

            if new_pin != confirm_pin:
                return render_template("update_pin.html", message="New PIN and Confirm PIN do not match")

            cursor.execute("update users_data set pin=%s where ac_no=%s", (new_pin, ac_no))

            connect_db.commit()

            return render_template("update_pin.html", message="PIN updated successfully!")

    return render_template("update_pin.html", message="")


@app.route("/cancel")
def cancel():
    session.clear()

    return render_template("logout.html")

if __name__ == "__main__":
    app.run(debug=True)