import os


from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, getUserPortfolio

# Configure application
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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    user = rows[0]
    userTransactions = db.execute("select * from transactions where user_id == ?",user["id"])

    userPortfolio = getUserPortfolio(userTransactions)


    # get the current price of each stock
    netWorth = user["cash"] # plus all the stocks
    for s in userPortfolio:
        stockApicall = lookup(s["symbol"])
        s["current_price"] = stockApicall["price"]
        # total portfolio worth
        netWorth = netWorth + round(s["quantity"] * s["current_price"],2)




    return render_template("index.html", userPortfolio=userPortfolio, cash=user["cash"], total=netWorth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # check if the company exists
        tickerSymbol = request.form.get("symbol").strip().upper()
        quantity = int(request.form.get("shares"))
    

        stockApicall = lookup(tickerSymbol)
        if stockApicall == None:
            return apology("invalid ticker symbol")

        #check if the user has the balance
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        user = rows[0]

        quotedPrice = stockApicall["price"]*quantity
        if not user["cash"] >= quotedPrice: # don't have enough cash
            return apology("you don't have enough money")

        #if yes update cash of user & the transaction db
        date_time = f'{datetime.now().date()} {datetime.now().strftime("%H:%M:%S")}'
        db.execute("UPDATE users SET cash = ? WHERE id == ?",round(user["cash"]-quotedPrice,2),user["id"])
        db.execute("INSERT INTO transactions (user_id,symbol,name,quantity,price,order_type,date_time) VALUES(?,?,?,?,?,?,?)",user["id"],stockApicall["symbol"],stockApicall["name"],quantity,stockApicall["price"],"buy",date_time)


        # redirect to the home page with a "Buy Order Completed feedback"
        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    user = rows[0]
    userTransactions = db.execute("select * from transactions where user_id == ?",user["id"])

    return render_template("/history.html",transactions=userTransactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # if post then take the stock ticker find the current price and how the info to the user
    if request.method == "POST":

        tickerSymbol = request.form.get("symbol").strip().upper()
        stockDetails = lookup(tickerSymbol)
        if stockDetails != None:
            stockQuote = f"A share of {stockDetails['name']}. ({stockDetails['symbol']}) costs $ {stockDetails['price']} "
        else:
            return apology("invalid ticker symbol")


        return render_template("quote.html", stockQuote = stockQuote)

    # show the form to the user to enter the stocks name
    else:
        return render_template("quote.html", stockQuote = None)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure that the username and password fields are not empty
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # get the username and password in variables
        username = request.form.get("username")
        password = request.form.get("password")
        passwordConfirm = request.form.get("confirmation")

        if password != passwordConfirm:
            return apology("PASSWORDS DON'T MATCH")

        # Check if the username already exsists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 0:
            return apology("the username already exists")


        # register the user in the database and save the id to session
        session["user_id"] = db.execute("INSERT INTO users (username,hash) VALUES(?,?)",username,generate_password_hash(password))

        # Redirect user to login form
        flash("Registered!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # get the user portfolio
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    user = rows[0]
    userTransactions = db.execute("select * from transactions where user_id == ?",user["id"])
    userPortfolio = getUserPortfolio(userTransactions)

    #names of all the stocks in user portfolio
    symbolIndx = []
    for s in userPortfolio:
        symbolIndx.append(s["symbol"])

    if request.method == "POST":


        # get the stockname and quantity to sell
        stockToSell = request.form.get("stockName")
        quantity = int(request.form.get("quantity"))

        # make sure he has that much amount to sell
        for s in userPortfolio:
            if s["symbol"] == stockToSell:
                if s["quantity"] >= quantity:
                    stockApicall = lookup(stockToSell)
                    totalSellPrice = stockApicall["price"]*quantity
                     #update db
                    date_time = f'{datetime.now().date()} {datetime.now().strftime("%H:%M:%S")}'
                    db.execute("UPDATE users SET cash = ? WHERE id == ?",round(user["cash"]+totalSellPrice,2),user["id"])
                    db.execute("INSERT INTO transactions (user_id,symbol,name,quantity,price,order_type,date_time) VALUES(?,?,?,?,?,?,?)",user["id"],stockApicall["symbol"],stockApicall["name"],quantity,stockApicall["price"],"sell",date_time)
                else:
                    return apology("enter a lower quantity")


        flash("Sold!")
        return redirect("/")
    else:
        return render_template("sell.html", stockNames=symbolIndx)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)



# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

