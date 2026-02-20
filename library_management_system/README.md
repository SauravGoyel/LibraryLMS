# 📚 Library Management System

A full-featured **web-based Library Management System** built with Python (Flask), SQLAlchemy, and Bootstrap 5.

> **MCA Major Project** — Kurukshetra University  
> Student: Rahul Kumar Sharma | Roll No.: MCA/2023/045  
> Guide: Dr. Priya Mehta

---

## 🌟 Features

### Admin Panel
- 📊 Dashboard with charts (monthly issues, genre distribution)
- 📖 Book management — Add, Edit, Delete, Search, Filter
- 👥 Member management — Register, Edit, Suspend, Delete
- 🔄 Issue & Return books with one click
- 💰 Automatic fine calculation (₹2/day overdue)
- 📈 Reports — Overdue books, top issued books, fines

### Member Portal
- 🔍 Browse complete book catalogue with search & filter
- 📋 View currently borrowed books with due dates
- ⚠️ Overdue alerts with fine amounts
- 👤 Profile management

### Security
- 🔐 Role-based access control (Admin / Member)
- 🔑 Password hashing with Werkzeug (pbkdf2:sha256)
- 🛡️ Session management, SQL injection prevention via ORM

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3.10+, Flask 2.3             |
| Database    | SQLite (dev) / MySQL 8.0 (prod)     |
| ORM         | Flask-SQLAlchemy                    |
| Auth        | Flask-Login                         |
| Frontend    | HTML5, CSS3, Bootstrap 5.3          |
| Charts      | Chart.js 4.4                        |

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/library-management-system.git
cd library-management-system
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

### 5. Open in browser
```
http://localhost:5000
```

### 6. Default Admin Login
```
Email:    admin@library.com
Password: admin123
```

---

## 🗄️ Database Setup

### SQLite (Default — Zero Config)
No setup needed! The app auto-creates `instance/library.db` on first run.

### MySQL (Production)
1. Create database:
```sql
CREATE DATABASE library_db;
```
2. Set environment variable:
```bash
export DATABASE_URL="mysql+pymysql://root:password@localhost/library_db"
```

---

## 🌐 Deploy on Render (Free Hosting)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:create_app()`
5. Add environment variables:
   - `SECRET_KEY` → any long random string
   - `DATABASE_URL` → your MySQL/PostgreSQL URL

---

## 📁 Project Structure

```
library-management-system/
│
├── app.py                  # Application factory
├── config.py               # Configuration settings
├── extensions.py           # Flask extensions (db, login_manager)
├── models.py               # SQLAlchemy models
├── requirements.txt        # Python dependencies
│
├── routes/
│   ├── auth.py             # Login, logout, register
│   ├── admin.py            # Admin panel routes
│   └── member.py           # Member portal routes
│
├── templates/
│   ├── base.html           # Base layout (sidebar + topbar)
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── books.html
│   │   ├── book_form.html
│   │   ├── members.html
│   │   ├── member_form.html
│   │   ├── transactions.html
│   │   ├── issue_book.html
│   │   └── reports.html
│   └── member/
│       ├── dashboard.html
│       ├── catalogue.html
│       ├── my_books.html
│       └── profile.html
│
└── static/
    ├── css/style.css
    └── js/main.js
```

---

## ⚙️ Configuration

Edit `config.py` to adjust:

| Setting | Default | Description |
|---------|---------|-------------|
| `FINE_PER_DAY` | 2 | Fine in ₹ per overdue day |
| `BORROW_DAYS` | 14 | Days before book is due |
| `MAX_BORROW_LIMIT` | 3 | Max books per member |

---

## 📸 Screenshots

| Admin Dashboard | Book Catalogue |
|---|---|
| Stats cards, charts, recent transactions | Grid view with search & filters |

---

## 📜 License

This project is developed for academic purposes as part of MCA curriculum at Kurukshetra University.

---

## 🙏 Acknowledgements

- Flask documentation — https://flask.palletsprojects.com/
- Bootstrap 5 — https://getbootstrap.com/
- Chart.js — https://www.chartjs.org/
- SQLAlchemy — https://www.sqlalchemy.org/
