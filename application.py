from flask import Flask, session, render_template, redirect, request
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

    
        db.execute("INSERT INTO all_tickets (user_id, from_city, to_city, passengers, cost, date, time) VALUES(:user_id, :from_city, :to_city, :passenger, :cost, :date, :time)", {'user_id': int(session["user_id"]), 'from_city': request.form.get("from"), 'to_city': request.form.get('to'), 'passenger': int(request.form.get("num")), 'cost': total_cost, 'date': date.today(), 'time': train_time})
                        
        db.commit()

        return redirect('payment')


        return render_template("ticket.html",user=user, full_ticket=full_ticket)

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

        db.execute("UPDATE all_tickets SET payment = :total, returned = :returned WHERE id = (SELECT max(id) FROM all_tickets)", {'total': total, 'returned': returned})

        db.commit()

        return redirect('/ticket')

    else:

        return render_template("payment.html", user=user, total_cost=total_cost)

    
    


    

