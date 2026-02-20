"""
====================================================
  LIBRARY MANAGEMENT SYSTEM - Single File App
  MCA Project | Kurukshetra University
  Run: python lms.py
  Open: http://localhost:5000
  Admin: admin@library.com / admin123
====================================================
"""

from flask import Flask, render_template_string, redirect, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from functools import wraps
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lms-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
FINE_PER_DAY = 2
BORROW_DAYS  = 14
MAX_BORROW   = 3

db           = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view          = 'login'
login_manager.login_message_category = 'warning'

# ── Models ────────────────────────────────────────────────────────────────────
class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def get_id(self):            return f'admin-{self.id}'

class Member(UserMixin, db.Model):
    __tablename__ = 'members'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone         = db.Column(db.String(15))
    address       = db.Column(db.Text)
    join_date     = db.Column(db.Date, default=date.today)
    status        = db.Column(db.String(10), default='active')
    transactions  = db.relationship('Transaction', backref='member', lazy=True)
    def check_password(self, p):  return check_password_hash(self.password_hash, p)
    def get_id(self):             return f'member-{self.id}'
    def active_borrows(self):     return Transaction.query.filter_by(member_id=self.id, status='issued').count()

class Book(db.Model):
    __tablename__  = 'books'
    id             = db.Column(db.Integer, primary_key=True)
    isbn           = db.Column(db.String(20), unique=True, nullable=False)
    title          = db.Column(db.String(200), nullable=False)
    author         = db.Column(db.String(100), nullable=False)
    publisher      = db.Column(db.String(100))
    year           = db.Column(db.Integer)
    genre          = db.Column(db.String(50))
    total_copies   = db.Column(db.Integer, default=1)
    avail_copies   = db.Column(db.Integer, default=1)
    transactions   = db.relationship('Transaction', backref='book', lazy=True)
    def is_available(self): return self.avail_copies > 0

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id            = db.Column(db.Integer, primary_key=True)
    book_id       = db.Column(db.Integer, db.ForeignKey('books.id'),   nullable=False)
    member_id     = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    issue_date    = db.Column(db.Date, default=date.today)
    due_date      = db.Column(db.Date)
    return_date   = db.Column(db.Date, nullable=True)
    fine_amount   = db.Column(db.Float, default=0.0)
    status        = db.Column(db.String(10), default='issued')
    def calculate_fine(self):
        c = self.return_date or date.today()
        return round((c - self.due_date).days * FINE_PER_DAY, 2) if c > self.due_date else 0.0
    def is_overdue(self): return self.status == 'issued' and date.today() > self.due_date

@login_manager.user_loader
def load_user(uid):
    if uid.startswith('admin-'):  return Admin.query.get(int(uid.split('-')[1]))
    if uid.startswith('member-'): return Member.query.get(int(uid.split('-')[1]))

# ── Decorators ────────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not isinstance(current_user, Admin):
            flash('Admin access required.', 'danger')
            return redirect('/login')
        return f(*a, **kw)
    return login_required(dec)

def member_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not isinstance(current_user, Member):
            flash('Please login as a member.', 'danger')
            return redirect('/login')
        return f(*a, **kw)
    return login_required(dec)

# ── Shared layout builder ─────────────────────────────────────────────────────
def page(content, extra_js=''):
    """Wrap any content string inside the full sidebar layout."""
    return render_template_string(
        LAYOUT_TMPL,
        page_content=content,
        extra_js=extra_js,
        today=date.today()
    )

# ══════════════════════════════════════════════════════════════════════════════
#  HTML – all in one place, no template inheritance
# ══════════════════════════════════════════════════════════════════════════════

# ── Shared layout (renders sidebar + topbar around {{ page_content }}) ────────
LAYOUT_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LibraryMS</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<style>
:root{--sb:240px;--primary:#4361ee}
body{background:#f4f6fb;font-family:'Segoe UI',sans-serif;margin:0}
.sidebar{position:fixed;top:0;left:0;bottom:0;width:var(--sb);background:#1a1f36;display:flex;flex-direction:column;z-index:1000;overflow-y:auto}
.sb-brand{padding:20px;font-size:1.15rem;font-weight:700;color:#fff;border-bottom:1px solid rgba(255,255,255,.1)}
.sb-nav{list-style:none;padding:10px 0;margin:0;flex:1}
.sb-nav a{display:flex;align-items:center;gap:10px;padding:10px 20px;color:#c8cfdf;text-decoration:none;font-size:.9rem;transition:.2s}
.sb-nav a:hover{background:rgba(255,255,255,.08);color:#fff}
.sb-nav a.active{background:var(--primary);color:#fff;font-weight:600}
.sb-nav a i{width:20px}
.sb-sec{padding:14px 20px 4px;font-size:.68rem;font-weight:700;letter-spacing:.08em;color:rgba(255,255,255,.3);text-transform:uppercase}
.sb-foot{padding:14px 20px;border-top:1px solid rgba(255,255,255,.1)}
.main{margin-left:var(--sb);min-height:100vh;display:flex;flex-direction:column}
.topbar{height:60px;background:#fff;border-bottom:1px solid #e8ecf3;display:flex;align-items:center;justify-content:space-between;padding:0 24px;position:sticky;top:0;z-index:500;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.pg{padding:24px}
.ph{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;padding-bottom:14px;border-bottom:1px solid #e8ecf3}
.ph h4{margin:0;font-size:1.2rem;font-weight:700}
.card{border:1px solid #e8ecf3;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.card-header{background:#fff;border-bottom:1px solid #e8ecf3;border-radius:12px 12px 0 0!important;padding:12px 18px}
.sc{border-radius:12px;padding:18px;display:flex;align-items:center;gap:14px;color:#fff}
.sb{background:linear-gradient(135deg,#4361ee,#3a0ca3)}
.sg{background:linear-gradient(135deg,#4cc9f0,#0096c7)}
.so{background:linear-gradient(135deg,#f8961e,#f3722c)}
.sr{background:linear-gradient(135deg,#f72585,#b5179e)}
.si{font-size:1.9rem;opacity:.85}.sv{font-size:1.9rem;font-weight:800;line-height:1}.sl{font-size:.8rem;opacity:.85;margin-top:2px}
.table th{font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:#4a5568}
.table td{vertical-align:middle;font-size:.88rem}
.bk-card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.06);border:1px solid #e8ecf3;transition:.2s;height:100%}
.bk-card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(0,0,0,.1)}
.bk-cover{background:linear-gradient(135deg,#4361ee,#3a0ca3);height:88px;display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.3);font-size:2.4rem;position:relative}
.bk-gbadge{position:absolute;top:7px;right:7px;background:rgba(255,255,255,.2);color:#fff;font-size:.67rem;padding:2px 7px;border-radius:20px}
.bk-info{padding:12px}.bk-title{font-weight:700;font-size:.87rem;color:#1a202c;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bk-author{font-size:.79rem;color:#718096;margin-bottom:5px}
.pav{width:76px;height:76px;border-radius:50%;background:linear-gradient(135deg,#4361ee,#7209b7);color:#fff;font-size:1.9rem;font-weight:700;display:flex;align-items:center;justify-content:center;margin:0 auto}
@media(max-width:768px){.sidebar{transform:translateX(-100%)}.main{margin-left:0}.sb-open .sidebar{transform:translateX(0)}}
</style>
</head>
<body>
<div class="sidebar" id="sidebar">
  <div class="sb-brand"><i class="bi bi-book-half me-2"></i>LibraryMS</div>
  <ul class="sb-nav">
    {% if current_user.is_authenticated %}
      {% if current_user.__class__.__name__ == 'Admin' %}
        <li><span class="sb-sec">Admin Panel</span></li>
        <li><a href="/admin/dashboard" class="{{ 'active' if request.path=='/admin/dashboard' }}"><i class="bi bi-speedometer2"></i>Dashboard</a></li>
        <li><a href="/admin/books"     class="{{ 'active' if '/admin/book' in request.path }}"><i class="bi bi-journals"></i>Books</a></li>
        <li><a href="/admin/members"   class="{{ 'active' if '/admin/member' in request.path }}"><i class="bi bi-people"></i>Members</a></li>
        <li><a href="/admin/transactions" class="{{ 'active' if '/admin/transaction' in request.path }}"><i class="bi bi-arrow-left-right"></i>Transactions</a></li>
        <li><a href="/admin/issue"     class="{{ 'active' if request.path=='/admin/issue' }}"><i class="bi bi-plus-circle"></i>Issue Book</a></li>
        <li><a href="/admin/reports"   class="{{ 'active' if request.path=='/admin/reports' }}"><i class="bi bi-bar-chart-line"></i>Reports</a></li>
      {% else %}
        <li><span class="sb-sec">Member Panel</span></li>
        <li><a href="/member/dashboard" class="{{ 'active' if request.path=='/member/dashboard' }}"><i class="bi bi-house"></i>Dashboard</a></li>
        <li><a href="/member/catalogue" class="{{ 'active' if request.path=='/member/catalogue' }}"><i class="bi bi-search"></i>Browse Books</a></li>
        <li><a href="/member/mybooks"   class="{{ 'active' if request.path=='/member/mybooks' }}"><i class="bi bi-bookmark-check"></i>My Books</a></li>
        <li><a href="/member/profile"   class="{{ 'active' if request.path=='/member/profile' }}"><i class="bi bi-person-circle"></i>Profile</a></li>
      {% endif %}
    {% endif %}
  </ul>
  <div class="sb-foot"><a href="/logout" class="text-danger text-decoration-none"><i class="bi bi-box-arrow-left me-2"></i>Logout</a></div>
</div>

<div class="main" id="main">
  <nav class="topbar">
    <button class="btn btn-sm btn-outline-secondary" id="tog"><i class="bi bi-list fs-5"></i></button>
    <div class="d-flex align-items-center gap-2">
      <span class="badge {{ 'bg-danger' if current_user.__class__.__name__=='Admin' else 'bg-primary' }}">
        {{ current_user.__class__.__name__ }}</span>
      <span class="fw-semibold">{{ current_user.name }}</span>
    </div>
  </nav>
  <div class="px-4 pt-3">
    {% with msgs = get_flashed_messages(with_categories=True) %}
      {% for cat, msg in msgs %}
        <div class="alert alert-{{ cat }} alert-dismissible fade show py-2">
          <i class="bi bi-info-circle me-2"></i>{{ msg }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endwith %}
  </div>
  <div class="pg">{{ page_content|safe }}</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
const tog=document.getElementById('tog');
if(tog) tog.addEventListener('click',()=>{
  const sb=document.getElementById('sidebar'),m=document.getElementById('main');
  if(window.innerWidth<=768){ document.body.classList.toggle('sb-open'); }
  else{
    const c=sb.style.transform==='translateX(-100%)';
    sb.style.transform=c?'':'translateX(-100%)';
    m.style.marginLeft=c?'var(--sb)':'0';
  }
});
document.querySelectorAll('.alert-dismissible').forEach(a=>
  setTimeout(()=>{try{bootstrap.Alert.getOrCreateInstance(a).close()}catch(e){}},4000));
</script>
{{ extra_js|safe }}
</body>
</html>"""

# ── Auth pages (no sidebar needed) ───────────────────────────────────────────
AUTH_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LibraryMS – {{ page_title }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<style>
body{background:linear-gradient(135deg,#1a1f36,#3a0ca3,#4361ee);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',sans-serif}
.ac{background:#fff;border-radius:20px;padding:38px;width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.al{width:62px;height:62px;border-radius:16px;background:linear-gradient(135deg,#4361ee,#3a0ca3);display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.7rem;margin:0 auto 14px}
</style>
</head>
<body>
<div class="ac">
  <div class="al"><i class="bi bi-book-half"></i></div>
  <h2 class="text-center fw-bold fs-4 mb-1">Library Management System</h2>
  <p class="text-center text-muted mb-4">Kurukshetra University</p>
  {% with msgs = get_flashed_messages(with_categories=True) %}
    {% for cat, msg in msgs %}<div class="alert alert-{{ cat }} py-2">{{ msg }}</div>{% endfor %}
  {% endwith %}
  {{ page_content|safe }}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

def auth_page(content):
    return render_template_string(AUTH_SHELL, page_content=content, page_title="Login")

# ══════════════════════════════════════════════════════════════════════════════
#  Route helpers – each returns a plain HTML string, page() wraps it
# ══════════════════════════════════════════════════════════════════════════════

def flash_html():
    """Renders flash messages (used inside page_content when needed)."""
    return ""   # layout already renders flashes

def _genres():
    return [g for (g,) in db.session.query(Book.genre).distinct().order_by(Book.genre).all() if g]

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect('/admin/dashboard' if isinstance(current_user, Admin) else '/member/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect('/')
    if request.method == 'POST':
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        role     = request.form.get('role','member')
        user = Admin.query.filter_by(email=email).first() if role=='admin' \
               else Member.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if isinstance(user, Member) and user.status == 'suspended':
                flash('Account suspended. Contact the librarian.', 'danger')
            else:
                login_user(user)
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect('/admin/dashboard' if isinstance(user, Admin) else '/member/dashboard')
        else:
            flash('Invalid email or password.', 'danger')

    content = """
    <div class="d-flex gap-2 mb-4">
      <input type="radio" class="btn-check" name="role" id="rA" value="admin" form="lf" autocomplete="off">
      <label class="btn btn-outline-danger flex-fill" for="rA"><i class="bi bi-shield-lock me-1"></i>Admin</label>
      <input type="radio" class="btn-check" name="role" id="rM" value="member" form="lf" autocomplete="off" checked>
      <label class="btn btn-outline-primary flex-fill" for="rM"><i class="bi bi-person me-1"></i>Member</label>
    </div>
    <form method="POST" id="lf">
      <div class="mb-3"><label class="form-label">Email</label>
        <div class="input-group"><span class="input-group-text"><i class="bi bi-envelope"></i></span>
        <input type="email" name="email" class="form-control" required autofocus placeholder="you@email.com"></div></div>
      <div class="mb-4"><label class="form-label">Password</label>
        <div class="input-group"><span class="input-group-text"><i class="bi bi-lock"></i></span>
        <input type="password" name="password" id="pwd" class="form-control" required>
        <button class="btn btn-outline-secondary" type="button"
          onclick="var p=document.getElementById('pwd');p.type=p.type==='password'?'text':'password'">
          <i class="bi bi-eye"></i></button></div></div>
      <button class="btn btn-primary w-100 btn-lg"><i class="bi bi-box-arrow-in-right me-2"></i>Sign In</button>
    </form>
    <hr class="my-3">
    <p class="text-center mb-1">New member? <a href="/register">Register here</a></p>
    <p class="text-center text-muted small mb-0"><strong>Demo Admin:</strong> admin@library.com / admin123</p>
    """
    return auth_page(content)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        if Member.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
        else:
            m = Member(name=request.form['name'].strip(), email=email,
                       password_hash=generate_password_hash(request.form['password']),
                       phone=request.form.get('phone','').strip(),
                       address=request.form.get('address','').strip())
            db.session.add(m); db.session.commit()
            flash('Registered! Please login.', 'success')
            return redirect('/login')
    content = """
    <form method="POST">
      <div class="mb-3"><label class="form-label">Full Name *</label><input type="text" name="name" class="form-control" required></div>
      <div class="mb-3"><label class="form-label">Email *</label><input type="email" name="email" class="form-control" required></div>
      <div class="mb-3"><label class="form-label">Password *</label><input type="password" name="password" class="form-control" required minlength="6"></div>
      <div class="mb-3"><label class="form-label">Phone</label><input type="tel" name="phone" class="form-control"></div>
      <div class="mb-4"><label class="form-label">Address</label><textarea name="address" class="form-control" rows="2"></textarea></div>
      <button class="btn btn-primary w-100 btn-lg">Register</button>
    </form>
    <hr class="my-3">
    <p class="text-center mb-0">Already registered? <a href="/login">Login</a></p>
    """
    return auth_page(content)

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.', 'info')
    return redirect('/login')

# ── ADMIN DASHBOARD ───────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    tb  = Book.query.count()
    tm  = Member.query.count()
    ai  = Transaction.query.filter_by(status='issued').count()
    od  = Transaction.query.filter(Transaction.status=='issued', Transaction.due_date < date.today()).count()
    txns = Transaction.query.order_by(Transaction.id.desc()).limit(8).all()
    gd  = db.session.query(Book.genre, func.count(Book.id)).group_by(Book.genre).all()
    mon = []
    for i in range(5,-1,-1):
        ms = date.today().replace(day=1) - timedelta(days=i*30)
        me = (ms.replace(day=28)+timedelta(days=4)).replace(day=1)
        c  = Transaction.query.filter(Transaction.issue_date>=ms, Transaction.issue_date<me).count()
        mon.append((ms.strftime('%b %Y'), c))
    ml = str([m[0] for m in mon]); mc = str([m[1] for m in mon])
    gl = str([g or 'Other' for g,_ in gd]); gc = str([c for _,c in gd])
    rows = ''.join(f"""<tr>
      <td class="text-muted">{t.id}</td>
      <td>{t.book.title[:40]}</td><td>{t.member.name}</td>
      <td>{t.issue_date}</td>
      <td class="{'text-danger fw-bold' if t.status=='issued' and t.due_date<date.today() else ''}">{t.due_date}</td>
      <td>{"<span class='badge bg-success'>Returned</span>" if t.status=='returned' else
           "<span class='badge bg-danger'>Overdue</span>" if t.due_date<date.today() else
           "<span class='badge bg-warning text-dark'>Issued</span>"}</td>
    </tr>""" for t in txns) or "<tr><td colspan='6' class='text-center text-muted py-4'>No transactions yet.</td></tr>"
    content = f"""
    <div class="ph"><h4><i class="bi bi-speedometer2 me-2"></i>Dashboard</h4>
      <span class="text-muted">Welcome, {current_user.name}</span></div>
    <div class="row g-3 mb-4">
      <div class="col-sm-6 col-xl-3"><div class="sc sb"><div class="si"><i class="bi bi-journals"></i></div><div><div class="sv">{tb}</div><div class="sl">Total Books</div></div></div></div>
      <div class="col-sm-6 col-xl-3"><div class="sc sg"><div class="si"><i class="bi bi-people"></i></div><div><div class="sv">{tm}</div><div class="sl">Members</div></div></div></div>
      <div class="col-sm-6 col-xl-3"><div class="sc so"><div class="si"><i class="bi bi-arrow-left-right"></i></div><div><div class="sv">{ai}</div><div class="sl">Active Issues</div></div></div></div>
      <div class="col-sm-6 col-xl-3"><div class="sc sr"><div class="si"><i class="bi bi-exclamation-triangle"></i></div><div><div class="sv">{od}</div><div class="sl">Overdue</div></div></div></div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-lg-7"><div class="card h-100"><div class="card-header"><h6 class="mb-0"><i class="bi bi-bar-chart me-2"></i>Monthly Issues</h6></div>
        <div class="card-body"><canvas id="mC" height="130"></canvas></div></div></div>
      <div class="col-lg-5"><div class="card h-100"><div class="card-header"><h6 class="mb-0"><i class="bi bi-pie-chart me-2"></i>Books by Genre</h6></div>
        <div class="card-body d-flex align-items-center justify-content-center"><canvas id="gC" height="200"></canvas></div></div></div>
    </div>
    <div class="card"><div class="card-header d-flex justify-content-between">
      <h6 class="mb-0"><i class="bi bi-clock-history me-2"></i>Recent Transactions</h6>
      <a href="/admin/transactions" class="btn btn-sm btn-outline-primary">View All</a></div>
      <div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>#</th><th>Book</th><th>Member</th><th>Issue Date</th><th>Due Date</th><th>Status</th></tr></thead>
        <tbody>{rows}</tbody></table></div></div></div>"""
    js = f"""<script>
new Chart(document.getElementById('mC'),{{type:'bar',data:{{labels:{ml},datasets:[{{label:'Issues',data:{mc},backgroundColor:'rgba(67,97,238,.7)',borderRadius:6,borderSkipped:false}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}}}}}});
new Chart(document.getElementById('gC'),{{type:'doughnut',data:{{labels:{gl},datasets:[{{data:{gc},backgroundColor:['#4361ee','#3a0ca3','#7209b7','#f72585','#4cc9f0','#4895ef'],borderWidth:2}}]}},options:{{plugins:{{legend:{{position:'right'}}}},cutout:'60%'}}}});
</script>"""
    return page(content, js)

# ── ADMIN BOOKS ───────────────────────────────────────────────────────────────
@app.route('/admin/books')
@admin_required
def admin_books():
    q = request.args.get('q',''); genre = request.args.get('genre','')
    qr = Book.query
    if q:     qr = qr.filter(Book.title.ilike(f'%{q}%')|Book.author.ilike(f'%{q}%')|Book.isbn.ilike(f'%{q}%'))
    if genre: qr = qr.filter_by(genre=genre)
    books  = qr.order_by(Book.title).all()
    genres = _genres()
    gopts  = ''.join(f'<option value="{g}" {"selected" if g==genre else ""}>{g}</option>' for g in genres)
    rows   = ''.join(f"""<tr>
      <td class="text-muted">{b.id}</td><td class="fw-semibold">{b.title}</td><td>{b.author}</td>
      <td><code>{b.isbn}</code></td>
      <td>{"<span class='badge bg-light text-dark border'>"+b.genre+"</span>" if b.genre else "–"}</td>
      <td>{b.year or "–"}</td><td class="text-center">{b.total_copies}</td>
      <td class="text-center"><span class="badge {'bg-success' if b.avail_copies>0 else 'bg-danger'}">{b.avail_copies}</span></td>
      <td class="text-center">
        <a href="/admin/books/edit/{b.id}" class="btn btn-sm btn-outline-primary me-1"><i class="bi bi-pencil"></i></a>
        <form method="POST" action="/admin/books/delete/{b.id}" class="d-inline"
              onsubmit="return confirm('Delete this book?')">
          <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button></form>
      </td></tr>""" for b in books) or "<tr><td colspan='9' class='text-center text-muted py-4'>No books found.</td></tr>"
    content = f"""
    <div class="ph"><h4><i class="bi bi-journals me-2"></i>Book Catalogue</h4>
      <a href="/admin/books/add" class="btn btn-primary"><i class="bi bi-plus-lg me-1"></i>Add Book</a></div>
    <div class="card mb-3"><div class="card-body"><form method="GET" class="row g-2">
      <div class="col-md-6"><div class="input-group"><span class="input-group-text"><i class="bi bi-search"></i></span>
        <input type="text" name="q" class="form-control" placeholder="Title, author, ISBN…" value="{q}"></div></div>
      <div class="col-md-3"><select name="genre" class="form-select"><option value="">All Genres</option>{gopts}</select></div>
      <div class="col-md-3 d-flex gap-2"><button class="btn btn-primary flex-fill">Filter</button>
        <a href="/admin/books" class="btn btn-outline-secondary">Clear</a></div>
    </form></div></div>
    <div class="card"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>#</th><th>Title</th><th>Author</th><th>ISBN</th><th>Genre</th>
        <th>Year</th><th class="text-center">Copies</th><th class="text-center">Available</th><th class="text-center">Actions</th></tr></thead>
      <tbody>{rows}</tbody></table></div></div></div>"""
    return page(content)

@app.route('/admin/books/add', methods=['GET','POST'])
@admin_required
def admin_add_book():
    if request.method == 'POST':
        isbn = request.form['isbn'].strip()
        if Book.query.filter_by(isbn=isbn).first():
            flash('ISBN already exists.', 'danger')
        else:
            c = int(request.form.get('total_copies',1))
            b = Book(isbn=isbn, title=request.form['title'].strip(),
                     author=request.form['author'].strip(),
                     publisher=request.form.get('publisher','').strip(),
                     year=request.form.get('year') or None,
                     genre=request.form.get('genre','').strip(),
                     total_copies=c, avail_copies=c)
            db.session.add(b); db.session.commit()
            flash(f'Book "{b.title}" added.', 'success'); return redirect('/admin/books')
    return page(_book_form(None))

@app.route('/admin/books/edit/<int:bid>', methods=['GET','POST'])
@admin_required
def admin_edit_book(bid):
    bk = Book.query.get_or_404(bid)
    if request.method == 'POST':
        isbn = request.form['isbn'].strip()
        ex   = Book.query.filter_by(isbn=isbn).first()
        if ex and ex.id != bid:
            flash('ISBN already in use.', 'danger')
        else:
            nt = int(request.form.get('total_copies',1)); diff = nt - bk.total_copies
            bk.isbn=isbn; bk.title=request.form['title'].strip(); bk.author=request.form['author'].strip()
            bk.publisher=request.form.get('publisher','').strip(); bk.year=request.form.get('year') or None
            bk.genre=request.form.get('genre','').strip(); bk.total_copies=nt
            bk.avail_copies=max(0, bk.avail_copies+diff)
            db.session.commit(); flash(f'Book updated.', 'success'); return redirect('/admin/books')
    return page(_book_form(bk))

def _book_form(b):
    action = "Edit Book" if b else "Add New Book"
    icon   = "pencil" if b else "plus-circle"
    return f"""
    <div class="ph"><h4><i class="bi bi-{icon} me-2"></i>{action}</h4>
      <a href="/admin/books" class="btn btn-outline-secondary"><i class="bi bi-arrow-left me-1"></i>Back</a></div>
    <div class="card" style="max-width:680px"><div class="card-body"><form method="POST"><div class="row g-3">
      <div class="col-md-8"><label class="form-label">Title *</label>
        <input type="text" name="title" class="form-control" required value="{''+b.title if b else ''}"></div>
      <div class="col-md-4"><label class="form-label">ISBN *</label>
        <input type="text" name="isbn" class="form-control" required value="{''+b.isbn if b else ''}"></div>
      <div class="col-md-6"><label class="form-label">Author *</label>
        <input type="text" name="author" class="form-control" required value="{''+b.author if b else ''}"></div>
      <div class="col-md-6"><label class="form-label">Publisher</label>
        <input type="text" name="publisher" class="form-control" value="{b.publisher or '' if b else ''}"></div>
      <div class="col-md-4"><label class="form-label">Year</label>
        <input type="number" name="year" class="form-control" value="{b.year or '' if b else ''}" min="1800" max="2099"></div>
      <div class="col-md-4"><label class="form-label">Genre</label>
        <input type="text" name="genre" class="form-control" value="{b.genre or '' if b else ''}"></div>
      <div class="col-md-4"><label class="form-label">Total Copies *</label>
        <input type="number" name="total_copies" class="form-control" required min="1" value="{b.total_copies if b else 1}"></div>
    </div>
    <div class="mt-4 d-flex gap-2">
      <button class="btn btn-primary px-4">{'Update Book' if b else 'Add Book'}</button>
      <a href="/admin/books" class="btn btn-outline-secondary">Cancel</a>
    </div></form></div></div>"""

@app.route('/admin/books/delete/<int:bid>', methods=['POST'])
@admin_required
def admin_delete_book(bid):
    bk = Book.query.get_or_404(bid)
    if Transaction.query.filter_by(book_id=bid, status='issued').count():
        flash(f'Cannot delete "{bk.title}" — has active issues.', 'danger')
    else:
        db.session.delete(bk); db.session.commit(); flash('Book deleted.', 'success')
    return redirect('/admin/books')

# ── ADMIN MEMBERS ─────────────────────────────────────────────────────────────
@app.route('/admin/members')
@admin_required
def admin_members():
    q = request.args.get('q','')
    qr = Member.query
    if q: qr = qr.filter(Member.name.ilike(f'%{q}%')|Member.email.ilike(f'%{q}%'))
    members = qr.order_by(Member.name).all()
    rows = ''.join(f"""<tr>
      <td class="text-muted">{m.id}</td><td class="fw-semibold">{m.name}</td>
      <td>{m.email}</td><td>{m.phone or '–'}</td><td>{m.join_date}</td>
      <td>{"<span class='badge bg-warning text-dark'>"+str(m.active_borrows())+"</span>" if m.active_borrows()>0 else "<span class='text-muted'>0</span>"}</td>
      <td><span class="badge {'bg-success' if m.status=='active' else 'bg-secondary'}">{m.status.capitalize()}</span></td>
      <td class="text-center">
        <a href="/admin/members/edit/{m.id}" class="btn btn-sm btn-outline-primary me-1"><i class="bi bi-pencil"></i></a>
        <form method="POST" action="/admin/members/delete/{m.id}" class="d-inline"
              onsubmit="return confirm('Delete member?')">
          <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button></form>
      </td></tr>""" for m in members) or "<tr><td colspan='8' class='text-center text-muted py-4'>No members found.</td></tr>"
    content = f"""
    <div class="ph"><h4><i class="bi bi-people me-2"></i>Members</h4>
      <a href="/admin/members/add" class="btn btn-primary"><i class="bi bi-person-plus me-1"></i>Add Member</a></div>
    <div class="card mb-3"><div class="card-body"><form method="GET" class="row g-2">
      <div class="col-md-8"><div class="input-group"><span class="input-group-text"><i class="bi bi-search"></i></span>
        <input type="text" name="q" class="form-control" placeholder="Name or email…" value="{q}"></div></div>
      <div class="col-md-4 d-flex gap-2"><button class="btn btn-primary flex-fill">Search</button>
        <a href="/admin/members" class="btn btn-outline-secondary">Clear</a></div>
    </form></div></div>
    <div class="card"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>#</th><th>Name</th><th>Email</th><th>Phone</th>
        <th>Joined</th><th>Borrows</th><th>Status</th><th class="text-center">Actions</th></tr></thead>
      <tbody>{rows}</tbody></table></div></div></div>"""
    return page(content)

@app.route('/admin/members/add', methods=['GET','POST'])
@admin_required
def admin_add_member():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        if Member.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
        else:
            m = Member(name=request.form['name'].strip(), email=email,
                       password_hash=generate_password_hash(request.form.get('password','member123')),
                       phone=request.form.get('phone','').strip(),
                       address=request.form.get('address','').strip(),
                       status=request.form.get('status','active'))
            db.session.add(m); db.session.commit()
            flash(f'Member "{m.name}" added.', 'success'); return redirect('/admin/members')
    return page(_member_form(None))

@app.route('/admin/members/edit/<int:mid>', methods=['GET','POST'])
@admin_required
def admin_edit_member(mid):
    m = Member.query.get_or_404(mid)
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        ex = Member.query.filter_by(email=email).first()
        if ex and ex.id != mid:
            flash('Email already in use.', 'danger')
        else:
            m.name=request.form['name'].strip(); m.email=email
            m.phone=request.form.get('phone','').strip(); m.address=request.form.get('address','').strip()
            m.status=request.form.get('status','active')
            if request.form.get('password'): m.password_hash=generate_password_hash(request.form['password'])
            db.session.commit(); flash('Member updated.', 'success'); return redirect('/admin/members')
    return page(_member_form(m))

def _member_form(m):
    action = "Edit Member" if m else "Add Member"
    icon   = "person-gear" if m else "person-plus"
    astatus= 'selected' if not m or m.status=='active' else ''
    sstatus= 'selected' if m and m.status=='suspended' else ''
    preq   = '' if m else 'required'
    return f"""
    <div class="ph"><h4><i class="bi bi-{icon} me-2"></i>{action}</h4>
      <a href="/admin/members" class="btn btn-outline-secondary"><i class="bi bi-arrow-left me-1"></i>Back</a></div>
    <div class="card" style="max-width:580px"><div class="card-body"><form method="POST"><div class="row g-3">
      <div class="col-md-6"><label class="form-label">Full Name *</label>
        <input type="text" name="name" class="form-control" required value="{m.name if m else ''}"></div>
      <div class="col-md-6"><label class="form-label">Email *</label>
        <input type="email" name="email" class="form-control" required value="{m.email if m else ''}"></div>
      <div class="col-md-6"><label class="form-label">Password {"(blank = no change)" if m else "*"}</label>
        <input type="password" name="password" class="form-control" {preq} minlength="6"></div>
      <div class="col-md-6"><label class="form-label">Phone</label>
        <input type="tel" name="phone" class="form-control" value="{m.phone or '' if m else ''}"></div>
      <div class="col-12"><label class="form-label">Address</label>
        <textarea name="address" class="form-control" rows="2">{m.address or '' if m else ''}</textarea></div>
      <div class="col-md-6"><label class="form-label">Status</label>
        <select name="status" class="form-select">
          <option value="active" {astatus}>Active</option>
          <option value="suspended" {sstatus}>Suspended</option>
        </select></div>
    </div>
    <div class="mt-4 d-flex gap-2">
      <button class="btn btn-primary px-4">{'Update' if m else 'Add Member'}</button>
      <a href="/admin/members" class="btn btn-outline-secondary">Cancel</a>
    </div></form></div></div>"""

@app.route('/admin/members/delete/<int:mid>', methods=['POST'])
@admin_required
def admin_delete_member(mid):
    m = Member.query.get_or_404(mid)
    if Transaction.query.filter_by(member_id=mid, status='issued').count():
        flash('Cannot delete — member has active issues.', 'danger')
    else:
        db.session.delete(m); db.session.commit(); flash('Member deleted.', 'success')
    return redirect('/admin/members')

# ── ADMIN TRANSACTIONS ────────────────────────────────────────────────────────
@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    status = request.args.get('status','')
    qr = Transaction.query
    if status: qr = qr.filter_by(status=status)
    txns = qr.order_by(Transaction.id.desc()).all()
    today = date.today()
    rows = ''.join(f"""<tr class="{'table-danger' if t.status=='issued' and t.due_date<today else ''}">
      <td class="text-muted">{t.id}</td>
      <td><div class="fw-semibold">{t.book.title[:35]}</div><small class="text-muted">{t.book.author}</small></td>
      <td>{t.member.name}</td><td>{t.issue_date}</td>
      <td class="{'text-danger fw-bold' if t.status=='issued' and t.due_date<today else ''}">{t.due_date}</td>
      <td>{t.return_date or '–'}</td>
      <td>{"<span class='text-danger fw-semibold'>₹"+f'{t.calculate_fine():.2f}'+"</span>" if t.calculate_fine()>0 else '–'}</td>
      <td>{"<span class='badge bg-success'>Returned</span>" if t.status=='returned'
           else "<span class='badge bg-danger'>Overdue</span>" if t.due_date<today
           else "<span class='badge bg-warning text-dark'>Issued</span>"}</td>
      <td class="text-center">{"<form method='POST' action='/admin/return/"+str(t.id)+"' onsubmit=\"return confirm('Mark returned?"+(f" Fine: ₹{t.calculate_fine():.2f}" if t.calculate_fine()>0 else "")+"')\"><button class='btn btn-sm btn-success'><i class='bi bi-check-circle me-1'></i>Return</button></form>" if t.status=='issued' else '–'}</td>
    </tr>""" for t in txns) or "<tr><td colspan='9' class='text-center text-muted py-4'>No transactions.</td></tr>"
    ab = 'btn-primary' if not status else 'btn-outline-secondary'
    ib = 'btn-warning' if status=='issued'   else 'btn-outline-warning'
    rb = 'btn-success' if status=='returned' else 'btn-outline-success'
    content = f"""
    <div class="ph"><h4><i class="bi bi-arrow-left-right me-2"></i>Transactions</h4>
      <a href="/admin/issue" class="btn btn-primary"><i class="bi bi-plus me-1"></i>Issue Book</a></div>
    <div class="card mb-3"><div class="card-body py-2 d-flex gap-2">
      <a href="/admin/transactions" class="btn btn-sm {ab}">All</a>
      <a href="/admin/transactions?status=issued" class="btn btn-sm {ib}">Issued</a>
      <a href="/admin/transactions?status=returned" class="btn btn-sm {rb}">Returned</a>
    </div></div>
    <div class="card"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>#</th><th>Book</th><th>Member</th><th>Issue Date</th>
        <th>Due Date</th><th>Return Date</th><th>Fine</th><th>Status</th><th class="text-center">Action</th></tr></thead>
      <tbody>{rows}</tbody></table></div></div></div>"""
    return page(content)

@app.route('/admin/issue', methods=['GET','POST'])
@admin_required
def admin_issue():
    if request.method == 'POST':
        bk = Book.query.get_or_404(int(request.form['book_id']))
        mb = Member.query.get_or_404(int(request.form['member_id']))
        if bk.avail_copies <= 0:
            flash('No copies available.', 'danger')
        elif mb.active_borrows() >= MAX_BORROW:
            flash(f'{mb.name} already has {MAX_BORROW} books issued.', 'danger')
        elif Transaction.query.filter_by(book_id=bk.id, member_id=mb.id, status='issued').first():
            flash('Member already has this book.', 'warning')
        else:
            t = Transaction(book_id=bk.id, member_id=mb.id, due_date=date.today()+timedelta(days=BORROW_DAYS))
            bk.avail_copies -= 1; db.session.add(t); db.session.commit()
            flash(f'"{bk.title}" issued to {mb.name}. Due: {t.due_date}', 'success')
            return redirect('/admin/transactions')
    books   = Book.query.filter(Book.avail_copies > 0).order_by(Book.title).all()
    members = Member.query.filter_by(status='active').order_by(Member.name).all()
    bopts = ''.join(f'<option value="{b.id}">{b.title} — {b.author} ({b.avail_copies} avail.)</option>' for b in books)
    mopts = ''.join(f'<option value="{m.id}">{m.name} ({m.email})</option>' for m in members)
    content = f"""
    <div class="ph"><h4><i class="bi bi-plus-circle me-2"></i>Issue Book</h4>
      <a href="/admin/transactions" class="btn btn-outline-secondary"><i class="bi bi-arrow-left me-1"></i>Back</a></div>
    <div class="card" style="max-width:540px"><div class="card-body">
      <div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>
        Issued for <strong>{BORROW_DAYS} days</strong>. Fine: <strong>₹{FINE_PER_DAY}/day</strong> overdue.</div>
      <form method="POST">
        <div class="mb-3"><label class="form-label">Select Book *</label>
          <select name="book_id" class="form-select" required id="bSel">
            <option value="">— Choose a book —</option>{bopts}</select></div>
        <div class="mb-3"><label class="form-label">Select Member *</label>
          <select name="member_id" class="form-select" required>
            <option value="">— Choose a member —</option>{mopts}</select></div>
        <div id="dInfo" class="alert alert-success d-none">
          <i class="bi bi-calendar-check me-2"></i>Due Date: <strong id="dDisp"></strong></div>
        <button class="btn btn-primary px-5 mt-2"><i class="bi bi-check-circle me-2"></i>Issue Book</button>
      </form>
    </div></div>"""
    js = f"""<script>
document.getElementById('bSel').addEventListener('change',function(){{
  const d=new Date(); d.setDate(d.getDate()+{BORROW_DAYS});
  const info=document.getElementById('dInfo');
  if(this.value){{document.getElementById('dDisp').textContent=d.toDateString();info.classList.remove('d-none');}}
  else info.classList.add('d-none');
}});
</script>"""
    return page(content, js)

@app.route('/admin/return/<int:tid>', methods=['POST'])
@admin_required
def admin_return(tid):
    t = Transaction.query.get_or_404(tid)
    if t.status == 'returned':
        flash('Already returned.', 'warning')
    else:
        t.return_date = date.today(); t.fine_amount = t.calculate_fine()
        t.status = 'returned'; t.book.avail_copies += 1; db.session.commit()
        if t.fine_amount > 0: flash(f'Book returned. Fine: ₹{t.fine_amount:.2f}', 'warning')
        else:                  flash('Book returned. No fine.', 'success')
    return redirect('/admin/transactions')

@app.route('/admin/reports')
@admin_required
def admin_reports():
    today    = date.today()
    overdue  = Transaction.query.filter(Transaction.status=='issued', Transaction.due_date<today).all()
    top      = db.session.query(Book.title, Book.author, func.count(Transaction.id).label('c'))\
                 .join(Transaction).group_by(Book.id).order_by(func.count(Transaction.id).desc()).limit(10).all()
    total_f  = db.session.query(func.sum(Transaction.fine_amount)).scalar() or 0

    od_rows  = ''.join(f"""<tr>
      <td class="fw-semibold">{t.book.title}</td>
      <td>{t.member.name}<br><small class="text-muted">{t.member.email}</small></td>
      <td>{t.issue_date}</td><td class="text-danger">{t.due_date}</td>
      <td><span class="badge bg-danger">{(today-t.due_date).days} days</span></td>
      <td class="text-danger fw-bold">₹{t.calculate_fine():.2f}</td>
    </tr>""" for t in overdue) or "<tr><td colspan='6' class='text-center text-muted py-3'>No overdue books!</td></tr>"

    medals = ['<i class="bi bi-trophy-fill text-warning"></i>',
              '<i class="bi bi-trophy-fill text-secondary"></i>',
              '<i class="bi bi-trophy-fill" style="color:#cd7f32"></i>']
    top_rows = ''.join(f"""<tr>
      <td>{medals[i] if i<3 else i+1}</td>
      <td class="fw-semibold">{title}</td><td>{author}</td>
      <td class="text-center"><span class="badge bg-primary rounded-pill">{cnt}</span></td>
    </tr>""" for i,(title,author,cnt) in enumerate(top)) or "<tr><td colspan='4' class='text-center text-muted py-3'>No data.</td></tr>"

    content = f"""
    <div class="ph"><h4><i class="bi bi-bar-chart-line me-2"></i>Reports & Analytics</h4></div>
    <div class="row g-3 mb-4">
      <div class="col-md-4"><div class="card text-center p-3 border-danger">
        <div class="text-danger fs-1 fw-bold">{len(overdue)}</div><div class="text-muted">Overdue Books</div></div></div>
      <div class="col-md-4"><div class="card text-center p-3 border-warning">
        <div class="text-warning fs-1 fw-bold">₹{total_f:.2f}</div><div class="text-muted">Fines Collected</div></div></div>
      <div class="col-md-4"><div class="card text-center p-3 border-info">
        <div class="text-info fs-1 fw-bold">{len(top)}</div><div class="text-muted">Top Books Tracked</div></div></div>
    </div>
    <div class="card mb-4"><div class="card-header bg-danger text-white">
      <h6 class="mb-0"><i class="bi bi-exclamation-triangle me-2"></i>Overdue Books ({len(overdue)})</h6></div>
      <div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Book</th><th>Member</th><th>Issue Date</th><th>Due Date</th><th>Days Late</th><th>Fine</th></tr></thead>
        <tbody>{od_rows}</tbody></table></div></div></div>
    <div class="card"><div class="card-header"><h6 class="mb-0"><i class="bi bi-trophy me-2"></i>Most Issued Books</h6></div>
      <div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Rank</th><th>Title</th><th>Author</th><th class="text-center">Times Issued</th></tr></thead>
        <tbody>{top_rows}</tbody></table></div></div></div>"""
    return page(content)

# ── MEMBER ────────────────────────────────────────────────────────────────────
@app.route('/member/dashboard')
@member_required
def member_dashboard():
    today  = date.today()
    active = Transaction.query.filter_by(member_id=current_user.id, status='issued').all()
    oc     = sum(1 for t in active if t.is_overdue())
    tb     = Book.query.count()
    rows   = ''.join(f"""<tr class="{'table-danger' if t.is_overdue() else ''}">
      <td class="fw-semibold">{t.book.title}</td><td>{t.book.author}</td>
      <td>{t.issue_date}</td>
      <td class="{'text-danger fw-bold' if t.is_overdue() else ''}">{t.due_date}</td>
      <td>{"<span class='badge bg-danger'>Overdue – Fine: ₹"+f'{t.calculate_fine():.2f}'+"</span>"
           if t.is_overdue()
           else "<span class='badge "+(
             'bg-warning text-dark' if (t.due_date-today).days<=3 else 'bg-success'
           )+"'>"+str((t.due_date-today).days)+" day"+(
             's' if (t.due_date-today).days!=1 else ''
           )+" left</span>"}</td>
    </tr>""" for t in active) or "<tr><td colspan='5' class='text-center text-muted py-4'>No books borrowed.</td></tr>"
    content = f"""
    <div class="ph"><h4><i class="bi bi-house me-2"></i>My Dashboard</h4></div>
    <div class="row g-3 mb-4">
      <div class="col-sm-4"><div class="sc sb"><div class="si"><i class="bi bi-book-half"></i></div><div><div class="sv">{len(active)}</div><div class="sl">Books Borrowed</div></div></div></div>
      <div class="col-sm-4"><div class="sc so"><div class="si"><i class="bi bi-exclamation-circle"></i></div><div><div class="sv">{oc}</div><div class="sl">Overdue</div></div></div></div>
      <div class="col-sm-4"><div class="sc sg"><div class="si"><i class="bi bi-journals"></i></div><div><div class="sv">{tb}</div><div class="sl">Books in Library</div></div></div></div>
    </div>
    <div class="card mb-4"><div class="card-header d-flex justify-content-between">
      <h6 class="mb-0"><i class="bi bi-bookmark-check me-2"></i>Currently Borrowed</h6>
      <a href="/member/mybooks" class="btn btn-sm btn-outline-primary">View All</a></div>
      <div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Book</th><th>Author</th><th>Issue Date</th><th>Due Date</th><th>Status</th></tr></thead>
        <tbody>{rows}</tbody></table></div></div></div>
    <div class="card bg-primary text-white"><div class="card-body d-flex justify-content-between align-items-center">
      <div><h5 class="mb-1">Looking for something to read?</h5>
        <p class="mb-0 opacity-75">Browse {tb} books in our catalogue.</p></div>
      <a href="/member/catalogue" class="btn btn-light text-primary fw-semibold">
        <i class="bi bi-search me-1"></i>Browse Catalogue</a>
    </div></div>"""
    return page(content)

@app.route('/member/catalogue')
@member_required
def member_catalogue():
    q     = request.args.get('q',''); genre = request.args.get('genre',''); avail = request.args.get('avail','')
    qr    = Book.query
    if q:     qr = qr.filter(Book.title.ilike(f'%{q}%')|Book.author.ilike(f'%{q}%')|Book.isbn.ilike(f'%{q}%'))
    if genre: qr = qr.filter_by(genre=genre)
    if avail: qr = qr.filter(Book.avail_copies > 0)
    books  = qr.order_by(Book.title).all()
    genres = _genres()
    gopts  = ''.join(f'<option value="{g}" {"selected" if g==genre else ""}>{g}</option>' for g in genres)
    cards  = ''.join(f"""<div class="col-sm-6 col-lg-4 col-xl-3">
      <div class="bk-card"><div class="bk-cover"><i class="bi bi-book"></i>
        {"<span class='bk-gbadge'>"+b.genre+"</span>" if b.genre else ""}
      </div>
      <div class="bk-info">
        <div class="bk-title" title="{b.title}">{b.title}</div>
        <div class="bk-author">{b.author}</div>
        <div class="mt-2">{"<span class='badge bg-success'><i class='bi bi-check-circle me-1'></i>"+str(b.avail_copies)+" Available</span>" if b.is_available() else "<span class='badge bg-danger'>Not Available</span>"}</div>
        <div class="text-muted small mt-1">ISBN: {b.isbn}</div>
      </div></div></div>""" for b in books) or """<div class="col-12 text-center text-muted py-5">
      <i class="bi bi-search fs-1 d-block mb-3 opacity-25"></i>No books found.</div>"""
    content = f"""
    <div class="ph"><h4><i class="bi bi-search me-2"></i>Browse Catalogue</h4></div>
    <div class="card mb-3"><div class="card-body"><form method="GET" class="row g-2">
      <div class="col-md-5"><div class="input-group"><span class="input-group-text"><i class="bi bi-search"></i></span>
        <input type="text" name="q" class="form-control" placeholder="Title, author, ISBN…" value="{q}"></div></div>
      <div class="col-md-3"><select name="genre" class="form-select"><option value="">All Genres</option>{gopts}</select></div>
      <div class="col-md-2"><select name="avail" class="form-select">
        <option value="">All Books</option><option value="1" {"selected" if avail else ""}>Available Only</option></select></div>
      <div class="col-md-2 d-flex gap-2"><button class="btn btn-primary flex-fill">Search</button>
        <a href="/member/catalogue" class="btn btn-outline-secondary">Clear</a></div>
    </form></div></div>
    <div class="row g-3">{cards}</div>"""
    return page(content)

@app.route('/member/mybooks')
@member_required
def member_mybooks():
    today   = date.today()
    active  = Transaction.query.filter_by(member_id=current_user.id, status='issued').all()
    history = Transaction.query.filter_by(member_id=current_user.id, status='returned').order_by(Transaction.id.desc()).all()
    ar = ''.join(f"""<tr class="{'table-danger' if t.is_overdue() else ''}">
      <td class="fw-semibold">{t.book.title}</td><td>{t.book.author}</td>
      <td>{t.book.genre or '–'}</td><td>{t.issue_date}</td>
      <td class="{'text-danger fw-bold' if t.is_overdue() else ''}">{t.due_date}</td>
      <td>{"<span class='badge bg-danger'>Overdue – Fine: ₹"+f'{t.calculate_fine():.2f}'+"</span>"
           if t.is_overdue() else "<span class='badge bg-success'>"+str((t.due_date-today).days)+" days left</span>"}</td>
    </tr>""" for t in active) or "<tr><td colspan='6' class='text-center text-muted py-4'>No active borrows.</td></tr>"
    hr = ''.join(f"""<tr>
      <td class="fw-semibold">{t.book.title}</td><td>{t.book.author}</td>
      <td>{t.issue_date}</td><td>{t.due_date}</td><td>{t.return_date}</td>
      <td>{"<span class='text-danger'>₹"+f'{t.fine_amount:.2f}'+"</span>" if t.fine_amount and t.fine_amount>0 else "<span class='text-success'>₹0.00</span>"}</td>
    </tr>""" for t in history) or "<tr><td colspan='6' class='text-center text-muted py-4'>No history yet.</td></tr>"
    content = f"""
    <div class="ph"><h4><i class="bi bi-bookmark-check me-2"></i>My Books</h4></div>
    <h6 class="fw-semibold mb-3 text-primary">Currently Borrowed</h6>
    <div class="card mb-4"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>Book</th><th>Author</th><th>Genre</th><th>Issue Date</th><th>Due Date</th><th>Status</th></tr></thead>
      <tbody>{ar}</tbody></table></div></div></div>
    <h6 class="fw-semibold mb-3 text-secondary">Borrowing History</h6>
    <div class="card"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>Book</th><th>Author</th><th>Issue Date</th><th>Due Date</th><th>Return Date</th><th>Fine</th></tr></thead>
      <tbody>{hr}</tbody></table></div></div></div>"""
    return page(content)

@app.route('/member/profile', methods=['GET','POST'])
@member_required
def member_profile():
    if request.method == 'POST':
        current_user.name    = request.form['name'].strip()
        current_user.phone   = request.form.get('phone','').strip()
        current_user.address = request.form.get('address','').strip()
        if request.form.get('password'):
            current_user.password_hash = generate_password_hash(request.form['password'])
        db.session.commit(); flash('Profile updated!', 'success')
    u = current_user
    content = f"""
    <div class="ph"><h4><i class="bi bi-person-circle me-2"></i>My Profile</h4></div>
    <div class="row g-3">
      <div class="col-md-4"><div class="card text-center p-4">
        <div class="pav mb-3">{u.name[0].upper()}</div>
        <h5>{u.name}</h5><p class="text-muted mb-1">{u.email}</p>
        <span class="badge bg-primary">Library Member</span><hr>
        <div class="text-start">
          <small class="text-muted d-block"><i class="bi bi-calendar me-2"></i>Joined: {u.join_date}</small>
          <small class="text-muted d-block mt-1"><i class="bi bi-phone me-2"></i>{u.phone or 'Not set'}</small>
        </div></div></div>
      <div class="col-md-8"><div class="card"><div class="card-header"><h6 class="mb-0">Edit Profile</h6></div>
        <div class="card-body"><form method="POST"><div class="row g-3">
          <div class="col-md-6"><label class="form-label">Full Name *</label>
            <input type="text" name="name" class="form-control" required value="{u.name}"></div>
          <div class="col-md-6"><label class="form-label">Email (read-only)</label>
            <input type="email" class="form-control" value="{u.email}" disabled></div>
          <div class="col-md-6"><label class="form-label">Phone</label>
            <input type="tel" name="phone" class="form-control" value="{u.phone or ''}"></div>
          <div class="col-md-6"><label class="form-label">New Password <small class="text-muted">(blank = no change)</small></label>
            <input type="password" name="password" class="form-control" minlength="6"></div>
          <div class="col-12"><label class="form-label">Address</label>
            <textarea name="address" class="form-control" rows="2">{u.address or ''}</textarea></div>
        </div>
        <button class="btn btn-primary mt-3"><i class="bi bi-check-lg me-1"></i>Save Changes</button>
        </form></div></div></div>
    </div>"""
    return page(content)

# ── Init & Run ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(email='admin@library.com').first():
            db.session.add(Admin(name='Library Admin', email='admin@library.com',
                                 password_hash=generate_password_hash('admin123')))
            db.session.commit()
        if Book.query.count() == 0:
            db.session.add_all([
                Book(isbn='978-0132350884', title='Clean Code',               author='Robert C. Martin',  publisher='Prentice Hall',  year=2008, genre='Programming',    total_copies=3, avail_copies=3),
                Book(isbn='978-0201633610', title='Design Patterns',          author='Gang of Four',       publisher='Addison-Wesley', year=1994, genre='Programming',    total_copies=2, avail_copies=2),
                Book(isbn='978-0134685991', title='Effective Java',           author='Joshua Bloch',       publisher='Addison-Wesley', year=2018, genre='Programming',    total_copies=2, avail_copies=2),
                Book(isbn='978-0596516499', title='JavaScript: The Good Parts',author='Douglas Crockford', publisher="O'Reilly",       year=2008, genre='Web Dev',        total_copies=3, avail_copies=3),
                Book(isbn='978-1491950296', title='Python for Data Analysis', author='Wes McKinney',       publisher="O'Reilly",       year=2017, genre='Data Science',   total_copies=2, avail_copies=2),
                Book(isbn='978-0131103627', title='The C Programming Language',author='Kernighan & Ritchie',publisher='Prentice Hall',  year=1988, genre='Programming',    total_copies=2, avail_copies=2),
                Book(isbn='978-1491901731', title='Intro to Machine Learning', author='Andriy Burkov',     publisher="O'Reilly",       year=2019, genre='Data Science',   total_copies=2, avail_copies=2),
                Book(isbn='978-0134494166', title='Clean Architecture',       author='Robert C. Martin',  publisher='Prentice Hall',  year=2017, genre='Programming',    total_copies=1, avail_copies=1),
            ])
            db.session.commit()
    print("\n" + "="*50)
    print("  Library Management System")
    print("  URL  : http://localhost:5000")
    print("  Admin: admin@library.com / admin123")
    print("="*50 + "\n")
    app.run(debug=True)