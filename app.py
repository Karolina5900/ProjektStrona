import os
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, UserMixin, RoleMixin, SQLAlchemyUserDatastore, current_user, login_required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///olx.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'developerskie')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get('SECURITY_PASSWORD_SALT', 'jakas-sol')
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

db = SQLAlchemy(app)

# Model
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
    category = db.relationship('Category', secondary=categories_olxs, backref=db.backref('olxs'))
    sold = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.fs_uniquifier'))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    description = db.Column(db.String(128))

class Category(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    description = db.Column(db.String(128))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)  # Wyamagane od wersji 4.0.0
    roles = db.relationship('Role', secondary=roles_user, backref=db.backref('users'))

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.fs_uniquifier:
            import uuid
            self.fs_uniquifier = str(uuid.uuid4())

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Routes
@app.route('/', methods=["GET", "POST"])
def index():
    ads = Olx.query.all()  # Pobranie wszystkich ogłoszeń
    categories = Category.query.all()  # Pobranie wszystkich dostępnych kategorii
    if request.method == "POST":
        # Pobieranie danych z formularza
        title = request.form.get("item_text")
        category_id = request.form.get("category")

        # Tworzenie nowego ogłoszenia
        new_ad = Olx(
            title=title,
            category=[Category.query.get(category_id)],  # Przypisanie kategorii
            user_id=current_user.get_id()
        )
        db.session.add(new_ad)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template('index.html', ads=ads, categories=categories)


@app.route("/add-olx", methods=["POST"])
@login_required
def add():
    new_task = Olx(
         title=request.form.get("item_text", "Bez tytułu"),  # Domyślna wartość, jeśli brak w formularzu
        description=request.form.get("description", "Brak opisu"),  # Opcjonalne pole
        user_id=current_user.get_id()
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("index"))

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         hashed_password = password  # W produkcji należy użyć bcrypt do haszowania
#         user = User(username=username, password=hashed_password)
#         db.session.add(user)
#         db.session.commit()
#         return redirect(url_for('login'))
#     return render_template('register.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         user = User.query.filter_by(username=username).first()
#         if user and user.password == password:  # Porównanie w produkcji po haszowaniu
#             login_user(user)
#             return redirect(url_for('index'))
#     return render_template('login.html')

# @app.route('/logout')
# def logout():
#     logout_user()
#     return redirect(url_for('index'))

# @app.route('/add_ad', methods=['POST'])
# @login_required
# def add_ad():
#     new_task = Add(
#         title=request.form["item_text"],
        
#         user_id=current_user.get_id()
#     )
#     db.session.add(new_task)
#     db.session.commit()
#     return redirect(url_for("index"))

# @app.route('/my_ads')
# @login_required
# def my_ads():
#     ads = Add.query.filter_by(user_id=current_user.id).all()
#     return render_template('my_ads.html', ads=ads)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5001, debug=True)