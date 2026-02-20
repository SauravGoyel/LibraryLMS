from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import Admin, Member
from extensions import db
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('member.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'member')

        if role == 'admin':
            user = Admin.query.filter_by(email=email).first()
        else:
            user = Member.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if role == 'member' and hasattr(user, 'status') and user.status == 'suspended':
                flash('Your account has been suspended. Please contact the librarian.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if isinstance(user, Admin):
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('member.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if Member.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('auth.register'))

        member = Member(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            phone=phone,
            address=address
        )
        db.session.add(member)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
