from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure secret key
app.config["SECRET_KEY"] = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///shop.db'    # File-based SQL database
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False    # Avoids SQLAlchemy warning
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True, default='')
    password = db.Column(db.String(255), nullable=False, default='')

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='')
    price = db.Column(db.Numeric, nullable=False)
    description = db.Column(db.Text)
    order = db.relationship('Order', backref='product')
    

class Buyer(db.Model):
    __tablename__ = "buyers"
    id = db.Column(db.Integer, primary_key=True)
    # User information
    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, default='')
    email = db.Column(db.String(255, collation='NOCASE'), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255), nullable=False, default='')
    order = db.relationship('Order', backref='owner')

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('buyers.id'))
    quantity = db.Column(db.Integer)
    total = db.Column(db.Numeric, nullable=False)
    date = db.Column(db.DateTime, nullable=False)

# Create all database tables
db.create_all()

if not User.query.filter(User.username == 'admin').first():
    user = User(
            username='admin',
            password=generate_password_hash('Pass1234'),
        )
    db.session.add(user)
    db.session.commit()


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    products = Product.query.order_by(Product.price).all()
    return render_template("index.html", products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Ensure username was submitted
        if not username:
            flash("must provide username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not password:
            flash("must provide password")
            return render_template("login.html")

        # Query database for username
        rows = User.query.filter(User.username == username).first()

        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows.password, password):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows.id

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

@app.route("/newproduct", methods=["GET", "POST"])
@login_required
def newproduct():
    """Sell shares of stock"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price")
        product = Product(
            name=name,
            price = price,
            description = description,
        )
        db.session.add(product)
        db.session.commit()
        flash("Added!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("newproduct.html")

@app.route("/buy", methods=["GET", "POST"])
def buy():
    if request.method == "POST":
        product_id = request.form.get("id")
        quantity = request.form.get("quantity")
        product = Product.query.filter(Product.id == product_id).first()
        if not product :
            flash("Select product")
            return redirect("/")
        total_row = round(float(product.price) * float(quantity),2)
        return render_template("buy.html", product=product, quantity=quantity, total_row=total_row)

@app.route("/addorder", methods=["GET", "POST"])
def addorder():
    if request.method == "POST":
        first_name = request.form.get("firstname")
        last_name = request.form.get("lastname")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        product_id = request.form.get("id")
        quantity = request.form.get("quantity")
        old_buyer  = Buyer.query.filter(Buyer.email == email).first()
        if not old_buyer:
            buyer = Buyer(
            first_name = first_name,
            last_name = last_name,
            email = email,
            phone = phone,
            address = address, 
            )
            db.session.add(buyer)
            db.session.commit()
        else:
            old_buyer.first_name = first_name
            old_buyer.last_name = last_name
            old_buyer.phone = phone
            old_buyer.address = address
            db.session.commit()
        owner = Buyer.query.filter(Buyer.email == email).first()

        product = Product.query.filter(Product.id == product_id).first()
        total = round(float(product.price) * float(quantity),2)
        order = Order(
            product_id = product_id,
            owner_id = owner.id,
            quantity = quantity,
            total = total,
            date = datetime.now(),
        )
    
        db.session.add(order)
        db.session.commit()
        flash("Thank you for your purchase!")
        return redirect("/")

@app.route("/orders")
@login_required
def orders():
    orders = db.session.query(Product, Buyer, Order).filter(
        Buyer.id == Order.owner_id,
        Product.id == Order.product_id).all()
    return render_template("orders.html", orders=orders)

@app.route("/about")
def about():
    return render_template("about.html")
