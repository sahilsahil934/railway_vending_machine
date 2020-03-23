from flask import Flask, session, render_template, redirect, request, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import *

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine("postgres://postgres:12345@localhost:5432/vending")
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():

    if session.get("user_id") is None:
        return redirect("/login")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    db.execute("DELETE FROM all_tickets WHERE user_id = :user_id AND payed = :payed" ,{'user_id': int(session["user_id"]), 'payed': 0})

    db.commit()

    if len(user) != 0:

        return render_template("index.html", user = user)

    else:
        return redirect("/login")


@app.route("/login", methods=['GET', 'POST'])
def login():

    session.clear()

    if request.method == "GET":

        return render_template("login.html")

    else:

        if not request.form.get("username"):
            return render_template("login.html", message = "Username Missing")
        if not request.form.get("password"):
            return render_template("login.html", message = "Password Missing")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 1 or not check_password_hash(row[0]["password"], request.form.get("password")):
            return render_template("login.html", message = "Username or Password is Incorrect!")

        session["user_id"] = row[0]["user_id"]

        session["ticket"] = 0

        return redirect("/")



@app.route("/register", methods=['GET', 'POST'])
def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("firstname"):
            return render_template("register.html", message = "FirstName Missing")

        if not request.form.get("lastname"):
            return render_template("register.html", message="LastName Missing")

        if not request.form.get("username"):
            return render_template("register.html", message = "Username Missing")

        if not request.form.get("password"):
            return render_template("register.html", message="Password Missing")

        if request.form.get("password") !=  request.form.get("confirmation"):
            return render_template("register.html", message="Password do not match")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 0:
            return render_template("register.html", message = "Username Already Exist")

        else:
            key = db.execute("INSERT INTO users (firstname, lastname, username, password) VALUES(:firstname, :lastname, :username, :password)",
                  {'firstname': request.form.get("firstname"), 'lastname': request.form.get("lastname"), 'username': request.form.get("username").lower(),
                   'password': generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)})

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        session["user_id"] = row[0]["user_id"]

        db.commit()

        session["ticket"] = 0

        return redirect("/")

    else:

        return render_template("register.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/generate", methods=['GET', 'POST'])
def generate():
 
    if session.get("user_id") is None:
        return redirect("/login")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
    all_tickets = db.execute("SELECT * FROM tickets").fetchall()

    if request.method == "POST":
        if not request.form.get("from"):
            return render_template("generate.html", user=user, all_tickets=all_tickets, message = "Source Missing")

        if not request.form.get("to"):
            return render_template("generate.html", user=user,all_tickets=all_tickets,  message="Destination Missing")

        if request.form.get("from") == request.form.get("to"):
            return render_template("generate.html", user=user,all_tickets=all_tickets,  message="Source and Destination can't be same")

        if not request.form.get("num"):
            return render_template("generate.html", user=user, all_tickets=all_tickets, message="Number of tickets Missing")

        ticket = db.execute("SELECT * FROM tickets where from_city = :from_city AND to_city = :to_city", {'from_city': request.form.get("from"), 'to_city': request.form.get("to")}).fetchall()

        if len(ticket) == 0:
            return render_template("generate.html", user=user, all_tickets=all_tickets, message="No Train available")

        total_cost = int(request.form.get("num")) * int(ticket[0]["cost"])
        
        train_time = ticket[0]["time"]

    
        db.execute("INSERT INTO all_tickets (user_id, from_city, to_city, passengers, cost, date, time, payed) VALUES(:user_id, :from_city, :to_city, :passenger, :cost, :date, :time, :payed)", {'user_id': int(session["user_id"]), 'from_city': request.form.get("from"), 'to_city': request.form.get('to'), 'passenger': int(request.form.get("num")), 'cost': total_cost, 'date': date.today(), 'time': train_time, 'payed': 0 })
                        
        db.commit()

        session["ticket"] = 1

        return redirect('payment')


    else:

        from_l = set()
        to_l = set()
        for i in all_tickets:
            from_l.add(i["from_city"])
            to_l.add(i["to_city"])

        return render_template("generate.html", user=user, from_l=from_l, to_l=to_l)


@app.route('/payment', methods=["GET", "POST"])
def payment():

    if session.get("user_id") is None:
        return redirect("/login")

    if session.get("ticket") == 0:
        return redirect("/generate")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    full_ticket = db.execute("SELECT * FROM all_tickets WHERE id = (SELECT max(id) FROM all_tickets)").fetchone()

    total_cost = full_ticket["cost"]

    if request.method == "POST":

        total = 0
        if request.form.get("num2000"):
            total = total + (2000 * int(request.form.get("num2000")))

        if request.form.get("num500"):
            total = total + (500 * int(request.form.get("num500")))

        if request.form.get("num200"):
            total = total + (200 * int(request.form.get("num200")))

        if request.form.get("num100"):
            total = total + (100 * int(request.form.get("num100")))

        if request.form.get("num50"):
            total = total + (50 * int(request.form.get("num500")))

        if request.form.get("num20"):
            total = total + (20 * int(request.form.get("num20")))

        if request.form.get("num10"):
            total = total + (10 * int(request.form.get("num10")))

        if request.form.get("num5"):
            total = total + (5 * int(request.form.get("num5")))

        if request.form.get("num2"):
            total = total + (2 * int(request.form.get("num2")))

        if request.form.get("num1"):
            total = total + (1 * int(request.form.get("num1")))

        returned = total - total_cost

        if returned < 0:

            message = "You payed " + str(total) + " only, here is you money, Pleae pay again"

            return render_template("payment.html", user=user, message=message, total_cost=total_cost)

        db.execute("UPDATE all_tickets SET payment = :total, returned = :returned WHERE id = (SELECT max(id) FROM all_tickets)", {'total': total, 'returned': returned})

        db.commit()

        return redirect('/ticket')

    else:

        return render_template("payment.html", user=user, total_cost=total_cost)


@app.route('/ticket')
def ticket():

    if session.get("user_id") is None:
        return redirect("/login")

    if session.get("ticket") == 0:
        return redirect("/generate")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    full_ticket = db.execute("SELECT * FROM all_tickets WHERE id = (SELECT max(id) FROM all_tickets)").fetchone()

    returned = full_ticket["returned"]

    return_notes = dict()

    if returned >= 2000:

        return_notes["notes_2000"] = returned // 2000
        returned = returned % 2000

    if returned >= 500:

        return_notes["notes_500"] = returned // 500
        returned = returned % 500

    if returned >= 200:

        return_notes["notes_200"] = returned // 200
        returned = returned % 200

    if returned >= 100:

        return_notes["notes_100"] = returned // 100
        returned = returned % 100

    if returned >= 50:

        return_notes["notes_50"] = returned // 50
        returned = returned % 50

    if returned >= 20:

        return_notes["notes_20"] = returned // 20
        returned = returned % 20


    if returned >= 10:

        return_notes["notes_10"] = returned // 10
        returned = returned % 10

    if returned >= 5:

        return_notes["coin_5"] = returned // 5
        returned = returned % 5

    if returned >= 2:

        return_notes["coin2_2"] = returned // 2
        returned = returned % 2

    if returned >= 1:

        return_notes["coin_1"] = returned // 1
        returned = returned % 1

    session["ticket"] = 0

    db.execute("UPDATE all_tickets SET payed = :value WHERE id = (SELECT max(id) FROM all_tickets)", {'value': 1})
    db.commit()

    return render_template("ticket.html", user=user, return_notes=return_notes, full_ticket=full_ticket)

        

@app.route("/password", methods=["GET", "POST"])
def password():

    if session.get("user_id") is None:
        return redirect("/login")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    if request.method == "GET":

        return render_template("password.html", user=user)

    else:

        if not request.form.get("old"):
            return render_template("password.html", message="Missing Old Password", user=user)

        elif not request.form.get("password"):
            return render_template("password.html", message="Missing new password", user=user)

        elif request.form.get("confirmation") != request.form.get("password"):
            return render_template("password.html", message="Password don't Match", user=user)

        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", {'user_id':session["user_id"]}).fetchall()

        if not check_password_hash(rows[0]["password"], request.form.get("old")):
            return render_template("password.html", message="Wrong old Password", user=user)

        else:
            db.execute("UPDATE users SET password = :hash WHERE user_id = :user_id",
                       {'user_id':session["user_id"],
                       'hash':generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)})

            db.commit()
        flash("Password Changed")
        return redirect('/index')


@app.route("/search", methods=["GET", "POST"])
def search():

    if session.get("user_id") is None:
        return redirect("/login")

    if request.method == "GET":

        return redirect("/")

    else:

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        if not request.form.get("search"):
            return redirect("/")

        rows = db.execute("SELECT * FROM tickets WHERE from_City LIKE :search", {'search': '%' + request.form.get("search").capitalize() + '%'}).fetchall()

        if rows != 0:
            return render_template("search.html", rows=rows, search=request.form.get("search"), user=user)
        else:
            return render_template("search.html", search=request.form.get("search"), user=user)


@app.route("/previous")
def previous():

    if session.get("user_id") is None:
        return redirect("/login")

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    rows = db.execute("SELECT * FROM all_tickets WHERE user_id = :user AND payed = :payed" ,{'user': int(session["user_id"]), 'payed': 1}).fetchall()

    if len(rows) != 0:

        return render_template("previous.html", user=user, rows=rows)

    else:

        return render_template("previous.html", user=user)
