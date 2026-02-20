from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
from config import Config


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"admin-{self.id}"


class Member(UserMixin, db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    join_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.Enum('active', 'suspended'), default='active')
    transactions = db.relationship('Transaction', backref='member', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"member-{self.id}"

    def active_borrows(self):
        return Transaction.query.filter_by(
            member_id=self.id, status='issued'
        ).count()


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    publisher = db.Column(db.String(100))
    year = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    total_copies = db.Column(db.Integer, default=1)
    avail_copies = db.Column(db.Integer, default=1)
    transactions = db.relationship('Transaction', backref='book', lazy=True)

    def is_available(self):
        return self.avail_copies > 0


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    return_date = db.Column(db.Date, nullable=True)
    fine_amount = db.Column(db.Numeric(10, 2), default=0.00)
    status = db.Column(db.Enum('issued', 'returned', 'overdue'), default='issued')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.due_date:
            self.due_date = date.today() + timedelta(days=Config.BORROW_DAYS)

    def calculate_fine(self):
        check_date = self.return_date or date.today()
        if check_date > self.due_date:
            days_late = (check_date - self.due_date).days
            return round(days_late * Config.FINE_PER_DAY, 2)
        return 0.00

    def is_overdue(self):
        if self.status == 'issued':
            return date.today() > self.due_date
        return False


@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('admin-'):
        return Admin.query.get(int(user_id.split('-')[1]))
    elif user_id.startswith('member-'):
        return Member.query.get(int(user_id.split('-')[1]))
    return None
