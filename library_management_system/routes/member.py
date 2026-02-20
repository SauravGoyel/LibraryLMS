from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import Member, Book, Transaction
from extensions import db
from datetime import date

member_bp = Blueprint('member', __name__)


def member_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not isinstance(current_user, Member):
            flash('Member access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return login_required(decorated)


@member_bp.route('/dashboard')
@member_required
def dashboard():
    active_txns = Transaction.query.filter_by(
        member_id=current_user.id, status='issued'
    ).all()
    history = Transaction.query.filter_by(
        member_id=current_user.id, status='returned'
    ).order_by(Transaction.id.desc()).limit(5).all()
    total_books = Book.query.count()
    return render_template('member/dashboard.html',
        active_txns=active_txns,
        history=history,
        total_books=total_books,
        today=date.today()
    )


@member_bp.route('/catalogue')
@member_required
def catalogue():
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '')
    availability = request.args.get('availability', '')
    page = request.args.get('page', 1, type=int)

    query = Book.query
    if q:
        query = query.filter(
            Book.title.ilike(f'%{q}%') |
            Book.author.ilike(f'%{q}%') |
            Book.isbn.ilike(f'%{q}%')
        )
    if genre:
        query = query.filter_by(genre=genre)
    if availability == 'available':
        query = query.filter(Book.avail_copies > 0)

    books = query.order_by(Book.title).paginate(page=page, per_page=12, error_out=False)
    genres = db.session.query(Book.genre).distinct().order_by(Book.genre).all()
    return render_template('member/catalogue.html', books=books, q=q, genre=genre, genres=genres, availability=availability)


@member_bp.route('/my-books')
@member_required
def my_books():
    active = Transaction.query.filter_by(
        member_id=current_user.id, status='issued'
    ).order_by(Transaction.due_date).all()
    history = Transaction.query.filter_by(
        member_id=current_user.id, status='returned'
    ).order_by(Transaction.id.desc()).all()
    return render_template('member/my_books.html', active=active, history=history, today=date.today())


@member_bp.route('/profile', methods=['GET', 'POST'])
@member_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        current_user.address = request.form.get('address', '').strip()
        if request.form.get('password'):
            current_user.set_password(request.form.get('password'))
        db.session.commit()
        flash('Profile updated successfully.', 'success')
    return render_template('member/profile.html')
