from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import Admin, Member, Book, Transaction
from extensions import db
from datetime import date, timedelta
from config import Config
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not isinstance(current_user, Admin):
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return login_required(decorated)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_books = Book.query.count()
    total_members = Member.query.count()
    active_issues = Transaction.query.filter_by(status='issued').count()
    overdue_count = Transaction.query.filter(
        Transaction.status == 'issued',
        Transaction.due_date < date.today()
    ).count()

    # Recent transactions
    recent_txns = Transaction.query.order_by(Transaction.id.desc()).limit(8).all()

    # Genre distribution for chart
    genre_data = db.session.query(
        Book.genre, func.count(Book.id)
    ).group_by(Book.genre).all()

    # Monthly issues for chart (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = date.today().replace(day=1) - timedelta(days=i * 30)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        count = Transaction.query.filter(
            Transaction.issue_date >= month_start,
            Transaction.issue_date < month_end
        ).count()
        monthly_data.append({'month': month_start.strftime('%b %Y'), 'count': count})

    return render_template('admin/dashboard.html',
        total_books=total_books,
        total_members=total_members,
        active_issues=active_issues,
        overdue_count=overdue_count,
        recent_txns=recent_txns,
        genre_data=genre_data,
        monthly_data=monthly_data
    )


# ── BOOKS ──────────────────────────────────────────────────────────────────────

@admin_bp.route('/books')
@admin_required
def books():
    q = request.args.get('q', '').strip()
    genre = request.args.get('genre', '')
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

    books_page = query.order_by(Book.title).paginate(page=page, per_page=10, error_out=False)
    genres = db.session.query(Book.genre).distinct().order_by(Book.genre).all()
    return render_template('admin/books.html', books=books_page, q=q, genre=genre, genres=genres)


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    if request.method == 'POST':
        isbn = request.form.get('isbn', '').strip()
        if Book.query.filter_by(isbn=isbn).first():
            flash('A book with this ISBN already exists.', 'danger')
            return render_template('admin/book_form.html', book=None)

        copies = int(request.form.get('total_copies', 1))
        book = Book(
            isbn=isbn,
            title=request.form.get('title', '').strip(),
            author=request.form.get('author', '').strip(),
            publisher=request.form.get('publisher', '').strip(),
            year=request.form.get('year') or None,
            genre=request.form.get('genre', '').strip(),
            total_copies=copies,
            avail_copies=copies
        )
        db.session.add(book)
        db.session.commit()
        flash(f'Book "{book.title}" added successfully.', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', book=None)


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        isbn = request.form.get('isbn', '').strip()
        existing = Book.query.filter_by(isbn=isbn).first()
        if existing and existing.id != book_id:
            flash('Another book with this ISBN already exists.', 'danger')
            return render_template('admin/book_form.html', book=book)

        old_total = book.total_copies
        new_total = int(request.form.get('total_copies', 1))
        diff = new_total - old_total

        book.isbn = isbn
        book.title = request.form.get('title', '').strip()
        book.author = request.form.get('author', '').strip()
        book.publisher = request.form.get('publisher', '').strip()
        book.year = request.form.get('year') or None
        book.genre = request.form.get('genre', '').strip()
        book.total_copies = new_total
        book.avail_copies = max(0, book.avail_copies + diff)

        db.session.commit()
        flash(f'Book "{book.title}" updated.', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', book=book)


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    active = Transaction.query.filter_by(book_id=book_id, status='issued').count()
    if active:
        flash(f'Cannot delete "{book.title}" — it has {active} active issue(s).', 'danger')
        return redirect(url_for('admin.books'))
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted.', 'success')
    return redirect(url_for('admin.books'))


# ── MEMBERS ────────────────────────────────────────────────────────────────────

@admin_bp.route('/members')
@admin_required
def members():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Member.query
    if q:
        query = query.filter(
            Member.name.ilike(f'%{q}%') |
            Member.email.ilike(f'%{q}%')
        )
    members_page = query.order_by(Member.name).paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/members.html', members=members_page, q=q)


@admin_bp.route('/members/add', methods=['GET', 'POST'])
@admin_required
def add_member():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if Member.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/member_form.html', member=None)

        from werkzeug.security import generate_password_hash
        member = Member(
            name=request.form.get('name', '').strip(),
            email=email,
            password_hash=generate_password_hash(request.form.get('password', 'member123')),
            phone=request.form.get('phone', '').strip(),
            address=request.form.get('address', '').strip(),
            status=request.form.get('status', 'active')
        )
        db.session.add(member)
        db.session.commit()
        flash(f'Member "{member.name}" added.', 'success')
        return redirect(url_for('admin.members'))

    return render_template('admin/member_form.html', member=None)


@admin_bp.route('/members/edit/<int:member_id>', methods=['GET', 'POST'])
@admin_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        existing = Member.query.filter_by(email=email).first()
        if existing and existing.id != member_id:
            flash('Email already in use.', 'danger')
            return render_template('admin/member_form.html', member=member)

        member.name = request.form.get('name', '').strip()
        member.email = email
        member.phone = request.form.get('phone', '').strip()
        member.address = request.form.get('address', '').strip()
        member.status = request.form.get('status', 'active')
        if request.form.get('password'):
            from werkzeug.security import generate_password_hash
            member.password_hash = generate_password_hash(request.form.get('password'))
        db.session.commit()
        flash(f'Member "{member.name}" updated.', 'success')
        return redirect(url_for('admin.members'))

    return render_template('admin/member_form.html', member=member)


@admin_bp.route('/members/delete/<int:member_id>', methods=['POST'])
@admin_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    active = Transaction.query.filter_by(member_id=member_id, status='issued').count()
    if active:
        flash(f'Cannot delete — member has {active} active issue(s).', 'danger')
        return redirect(url_for('admin.members'))
    db.session.delete(member)
    db.session.commit()
    flash(f'Member "{member.name}" deleted.', 'success')
    return redirect(url_for('admin.members'))


# ── TRANSACTIONS ───────────────────────────────────────────────────────────────

@admin_bp.route('/transactions')
@admin_required
def transactions():
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    query = Transaction.query
    if status:
        query = query.filter_by(status=status)
    txns = query.order_by(Transaction.id.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/transactions.html', txns=txns, status=status, today=date.today())


@admin_bp.route('/transactions/issue', methods=['GET', 'POST'])
@admin_required
def issue_book():
    books = Book.query.filter(Book.avail_copies > 0).order_by(Book.title).all()
    members = Member.query.filter_by(status='active').order_by(Member.name).all()

    if request.method == 'POST':
        book_id = int(request.form.get('book_id'))
        member_id = int(request.form.get('member_id'))

        book = Book.query.get_or_404(book_id)
        member = Member.query.get_or_404(member_id)

        if book.avail_copies <= 0:
            flash('No copies available for this book.', 'danger')
            return redirect(url_for('admin.issue_book'))

        if member.active_borrows() >= Config.MAX_BORROW_LIMIT:
            flash(f'{member.name} already has {Config.MAX_BORROW_LIMIT} books issued.', 'danger')
            return redirect(url_for('admin.issue_book'))

        # Check if member already has this book
        existing = Transaction.query.filter_by(
            book_id=book_id, member_id=member_id, status='issued'
        ).first()
        if existing:
            flash('This member already has this book issued.', 'warning')
            return redirect(url_for('admin.issue_book'))

        txn = Transaction(book_id=book_id, member_id=member_id)
        book.avail_copies -= 1
        db.session.add(txn)
        db.session.commit()
        flash(f'"{book.title}" issued to {member.name}. Due: {txn.due_date}', 'success')
        return redirect(url_for('admin.transactions'))

    return render_template('admin/issue_book.html', books=books, members=members)


@admin_bp.route('/transactions/return/<int:txn_id>', methods=['POST'])
@admin_required
def return_book(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.status == 'returned':
        flash('This book has already been returned.', 'warning')
        return redirect(url_for('admin.transactions'))

    txn.return_date = date.today()
    txn.fine_amount = txn.calculate_fine()
    txn.status = 'returned'
    txn.book.avail_copies += 1
    db.session.commit()

    if txn.fine_amount > 0:
        flash(f'Book returned. Fine collected: ₹{txn.fine_amount}', 'warning')
    else:
        flash('Book returned successfully. No fine.', 'success')
    return redirect(url_for('admin.transactions'))


# ── REPORTS ────────────────────────────────────────────────────────────────────

@admin_bp.route('/reports')
@admin_required
def reports():
    # Overdue books
    overdue = Transaction.query.filter(
        Transaction.status == 'issued',
        Transaction.due_date < date.today()
    ).all()

    # Most issued books
    top_books = db.session.query(
        Book.title, Book.author, func.count(Transaction.id).label('issue_count')
    ).join(Transaction, Book.id == Transaction.book_id
    ).group_by(Book.id).order_by(func.count(Transaction.id).desc()).limit(10).all()

    # Total fine collected
    total_fine = db.session.query(func.sum(Transaction.fine_amount)).scalar() or 0

    # Members with pending fines
    pending_fines = Transaction.query.filter(
        Transaction.status == 'issued',
        Transaction.due_date < date.today()
    ).all()

    return render_template('admin/reports.html',
        overdue=overdue,
        top_books=top_books,
        total_fine=total_fine,
        pending_fines=pending_fines,
        today=date.today()
    )
