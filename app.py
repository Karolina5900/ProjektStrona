import os
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, UserMixin, RoleMixin, SQLAlchemyUserDatastore, current_user, login_required, logout_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///olx.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'developerskie')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get('SECURITY_PASSWORD_SALT', 'jakas-sol')
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

db = SQLAlchemy(app)


roles_user = db.Table(
    'roles_users',
    db.Column('user_id', db.ForeignKey('user.id')),
    db.Column('role_id', db.ForeignKey('role.id')),
)

categories_olxs = db.Table(
    'categories_olxs',
    db.Column('olx_id', db.ForeignKey('olx.id')),
    db.Column('category_id', db.ForeignKey('category.id')),
)

class Olx(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False, default="Brak opisu")
    price = db.Column(db.Float, nullable=False, default=0.0) 
    category = db.relationship('Category', secondary=categories_olxs, backref=db.backref('olxs'))
    sold = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.fs_uniquifier'))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    description = db.Column(db.String(128))

class Category(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.String(128))

    def __repr__(self):
        return f'<Category {self.name}>'

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('user.fs_uniquifier'))
    olx_id = db.Column(db.Integer, db.ForeignKey('olx.id'))
    olx = db.relationship('Olx', backref='cart_items')
    user = db.relationship('User', backref='cart_items')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)  
    roles = db.relationship('Role', secondary=roles_user, backref=db.backref('users'))

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.fs_uniquifier:
            import uuid
            self.fs_uniquifier = str(uuid.uuid4())

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)



@app.route('/')
def index():
    ads = Olx.query.all()
    categories = Category.query.all() 
    return render_template('index.html', ads=ads, categories=categories)

@app.route("/add-olx", methods=["POST"])
@login_required
def add():
    title = request.form.get("item_text", "Bez tytułu")
    description = request.form.get("description", "Brak opisu")
    price = request.form.get("price", 0.0)  
    category_id = request.form.get("category")  

    
    if not category_id:
        return redirect(url_for("index"))
        
    category = Category.query.get_or_404(int(category_id))
   
    new_task = Olx(
        title=title,
        description=description,
        price=float(price), 
        category=[category], 
        user_id=current_user.get_id()
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("index"))


@app.before_request
def create_default_categories():
    if Category.query.count() == 0:
        categories = ['Elektronika', 'Motoryzacja', 'Nieruchomości', 'Usługi', 'Praca', 'Różne']
        for category_name in categories:
            category = Category(name=category_name)
            db.session.add(category)
        db.session.commit()

@app.route('/add_to_cart/<int:ad_id>', methods=['POST'])
@login_required
def add_to_cart(ad_id):
    ad = Olx.query.get_or_404(ad_id)
    if ad.user_id == current_user.get_id():
        return redirect(url_for('index'))  # Nie można dodać swojego przedmiotu do koszyka
    cart_item = CartItem(user_id=current_user.get_id(), olx_id=ad_id)
    db.session.add(cart_item)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.get_id()).all()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/remove_from_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.get_id():
        return redirect(url_for('view_cart'))
    db.session.delete(cart_item)
    db.session.commit()
    return redirect(url_for('view_cart'))


@app.route('/toggle_sold/<int:ad_id>', methods=["POST"])
@login_required
def toggle_sold(ad_id):
    ad = Olx.query.get_or_404(ad_id)
    if ad.user_id != current_user.get_id():
        return redirect(url_for('index'))
    
    ad.sold = not ad.sold 
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5001, debug=True)