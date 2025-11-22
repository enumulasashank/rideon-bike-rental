
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'rideon_bike_rental.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class Customer(db.Model, UserMixin):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    def get_id(self):
        return str(self.customer_id)

class Location(db.Model):
    __tablename__ = 'locations'
    location_id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(120))
    address = db.Column(db.String(255))

class Bike(db.Model):
    __tablename__ = 'bikes'
    bike_id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(120))
    type = db.Column(db.String(80))
    status = db.Column(db.String(40))
    rental_rate = db.Column(db.Float)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'))

class Rental(db.Model):
    __tablename__ = 'rentals'
    rental_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    bike_id = db.Column(db.Integer, db.ForeignKey('bikes.bike_id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'))
    rental_start = db.Column(db.String(30))
    rental_end = db.Column(db.String(30))
    total_cost = db.Column(db.Float)

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True)
    rental_id = db.Column(db.Integer, db.ForeignKey('rentals.rental_id'))
    amount = db.Column(db.Float)
    payment_date = db.Column(db.String(30))
    payment_method = db.Column(db.String(40))

@login_manager.user_loader
def load_user(user_id):
    return Customer.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('bikes'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if Customer.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        pw = generate_password_hash(request.form['password'])
        user = Customer(first_name=request.form.get('first_name'),
                        last_name=request.form.get('last_name'),
                        email=email,
                        phone=request.form.get('phone'),
                        password_hash=pw)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registered and logged in', 'success')
        return redirect(url_for('bikes'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = Customer.query.filter_by(email=request.form['email']).first()
        print("************", user.password_hash)
        print(user.password_hash,"**", request.form['password'])
        print("-------", user.password_hash == request.form['password'])
        if user and user.password_hash == request.form['password']:
            login_user(user)
            flash('Logged in', 'success')
            return redirect(url_for('bikes'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/bikes')
@login_required
def bikes():
    items = Bike.query.all()
    return render_template('bikes.html', bikes=items)

@app.route('/bikes/create', methods=['GET','POST'])
@login_required
def create_bike():
    if request.method == 'POST':
        b = Bike(model=request.form['model'],
                 type=request.form['type'],
                 status=request.form['status'],
                 rental_rate=float(request.form['rental_rate'] or 0),
                 location_id=int(request.form.get('location_id') or 0))
        db.session.add(b); db.session.commit()
        flash('Bike created', 'success'); return redirect(url_for('bikes'))
    locs = Location.query.all()
    return render_template('bike_edit.html', bike=None, locations=locs)

@app.route('/bikes/edit/<int:bike_id>', methods=['GET','POST'])
@login_required
def edit_bike(bike_id):
    b = Bike.query.get_or_404(bike_id)
    if request.method == 'POST':
        b.model = request.form['model']; b.type = request.form['type']
        b.status = request.form['status']; b.rental_rate = float(request.form['rental_rate'] or 0)
        b.location_id = int(request.form.get('location_id') or 0)
        db.session.commit(); flash('Bike updated', 'success'); return redirect(url_for('bikes'))
    locs = Location.query.all(); return render_template('bike_edit.html', bike=b, locations=locs)

@app.route('/bikes/delete/<int:bike_id>', methods=['POST'])
@login_required
def delete_bike(bike_id):
    b = Bike.query.get_or_404(bike_id); db.session.delete(b); db.session.commit()
    flash('Bike deleted', 'info'); return redirect(url_for('bikes'))

@app.route('/rentals')
@login_required
def rentals_list():
    items = Rental.query.all()
    return render_template('rentals.html', rentals=items)

@app.route('/rentals/create', methods=['GET','POST'])
@login_required
def create_rental():
    if request.method == 'POST':
        total = float(request.form.get('total_cost') or 0)
        r = Rental(customer_id=int(request.form['customer_id']),
                   bike_id=int(request.form['bike_id']),
                   location_id=int(request.form['location_id']),
                   rental_start=request.form['rental_start'],
                   rental_end=request.form['rental_end'],
                   total_cost=total)
        db.session.add(r); db.session.commit()
        flash('Rental created', 'success'); return redirect(url_for('rentals_list'))
    bikes = Bike.query.all(); customers = Customer.query.all(); locs = Location.query.all()
    return render_template('rental_edit.html', bikes=bikes, customers=customers, locations=locs)

@app.route('/payments')
@login_required
def payments_list():
    items = Payment.query.all(); return render_template('payments.html', payments=items)

@app.route('/payments/create', methods=['GET','POST'])
@login_required
def create_payment():
    if request.method == 'POST':
        p = Payment(rental_id=int(request.form['rental_id']), amount=float(request.form['amount']),
                    payment_date=request.form.get('payment_date'), payment_method=request.form.get('payment_method'))
        db.session.add(p); db.session.commit(); flash('Payment recorded', 'success'); return redirect(url_for('payments_list'))
    rentals = Rental.query.all(); return render_template('payment_edit.html', rentals=rentals)

@app.route('/dashboard')
@login_required
def dashboard():
    q = db.session.query(Location.location_name, db.func.count(Rental.rental_id)).join(Rental, Rental.location_id==Location.location_id, isouter=True).group_by(Location.location_name).all()
    labels = [r[0] for r in q]; values = [int(r[1]) for r in q]
    return render_template('dashboard.html', labels=labels, values=values)

@app.route('/api/rentals_by_location')
@login_required
def api_rentals_location():
    q = db.session.query(Location.location_name, db.func.count(Rental.rental_id)).join(Rental, Rental.location_id==Location.location_id, isouter=True).group_by(Location.location_name).all()
    return jsonify([{ "location": r[0], "count": int(r[1]) } for r in q])

if __name__ == '__main__':
    with app.app_context():  # <-- add this
        db.create_all()  # creates all tables based on models
    app.run(debug=True)
