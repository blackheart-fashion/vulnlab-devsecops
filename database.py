"""
database.py
Seeds a SQLite DB with sample data.
NOTE: Passwords are stored in PLAINTEXT on purpose (Vuln #9 - Sensitive Data Exposure).
This is an INTENTIONALLY INSECURE training application. Do not use any pattern
from this file in production code.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "vulnapp.db")


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,   -- plaintext (intentional)
            email TEXT,
            role TEXT DEFAULT 'user',
            secret_note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL
        )
    """)

    users = [
        ("admin", "Admin@123", "admin@vulnlab.local", "admin", "Flag{idor_admin_note_1337}"),
        ("pawan", "pawan123", "pawan@vulnlab.local", "user", "just a regular note"),
        ("riya", "riya2024", "riya@vulnlab.local", "user", "riya's private diary entry"),
        ("test", "test", "test@vulnlab.local", "user", "test account, nothing interesting"),
    ]
    cur.executemany(
        "INSERT INTO users (username, password, email, role, secret_note) VALUES (?, ?, ?, ?, ?)",
        users,
    )

    comments = [
        ("admin", "Welcome to the Vuln Lab demo app!"),
        ("pawan", "Try breaking the login form 😉"),
    ]
    cur.executemany("INSERT INTO comments (username, comment) VALUES (?, ?)", comments)

    products = [
        ("Laptop", "15 inch, 16GB RAM", 55000.0),
        ("Keyboard", "Mechanical, RGB", 3200.0),
        ("Mouse", "Wireless ergonomic", 999.0),
        ("Monitor", "27 inch 144Hz", 21000.0),
    ]
    cur.executemany("INSERT INTO products (name, description, price) VALUES (?, ?, ?)", products)

    conn.commit()
    conn.close()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
