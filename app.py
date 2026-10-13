"""
=====================================================================
 VULN-LAB — Intentionally Vulnerable Web Application (Training Use)
=====================================================================
Purpose : Classroom / workshop demo app for live pentesting sessions.
Author  : Generated for TSN Security training program
WARNING : This application is DELIBERATELY INSECURE. It contains real,
          exploitable OWASP Top-10 style vulnerabilities on purpose so
          students can attack it in a controlled lab / isolated VM /
          container network.

          DO NOT deploy this on the public internet or on any shared
          network. Run it only inside an isolated Docker network, a
          lab VLAN, or a sandboxed VM that students access locally.

See VULNERABILITIES.md for a full exploitation walkthrough you can
use live in class.
=====================================================================
"""

import os
import sqlite3
import subprocess
import requests
from flask import (
    Flask, request, render_template, redirect, url_for,
    session, send_from_directory, g, make_response
)
from database import init_db, get_conn, DB_PATH

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# VULN #18 - Security Misconfiguration: hardcoded weak secret + debug mode
# VULN #20 - Hardcoded/Weak Secret Key (used to forge signed session cookies)
app.config["SECRET_KEY"] = "super-secret-key-123"  # intentionally weak/hardcoded
app.config["DEBUG"] = True  # verbose stack traces exposed to users (intentional)

# VULN #15 - Insecure session cookie flags (HttpOnly off => JS/XSS can steal
# the session cookie; SameSite off => cookie sent on cross-site requests,
# which also powers the CSRF demo).
app.config["SESSION_COOKIE_HTTPONLY"] = False   # should be True in production
app.config["SESSION_COOKIE_SAMESITE"] = None    # should be "Lax" or "Strict"
app.config["SESSION_COOKIE_SECURE"] = False     # should be True when served over HTTPS


@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", user=session.get("username"))


# ---------------------------------------------------------------------------
# VULN #1 - SQL INJECTION (classic, string-concatenated query)
# Demo payload (username field):   admin' --
# Demo payload (bypass):           ' OR '1'='1' --
#
# VULN #16 - NO RATE LIMITING / BRUTE FORCE: unlimited login attempts, no
# lockout, no delay, no CAPTCHA. Demo with Hydra/Burp Intruder.
#
# VULN #13 - OPEN REDIRECT: ?next= is trusted blindly after a successful
# login. Demo: /login?next=https://evil-phish.example
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    next_url = request.args.get("next", "")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        next_url = request.form.get("next", next_url)

        conn = get_conn()
        cur = conn.cursor()
        # INTENTIONALLY VULNERABLE: raw string concatenation, no parameterization
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        try:
            cur.execute(query)
            row = cur.fetchone()
        except sqlite3.OperationalError as e:
            # VULN #18 continued: leaking raw DB error to the client
            return render_template("login.html", error=f"DB error: {e} | Query: {query}", next_url=next_url)
        conn.close()

        if row:
            # VULN #14 - Session Fixation: session is never rotated/regenerated
            # on login -- same cookie before and after auth, so an attacker who
            # fixes the victim's cookie beforehand inherits their logged-in session.
            # Also no CSRF protection anywhere in the app (VULN #10).
            session["username"] = row["username"]
            session["role"] = row["role"]
            session["user_id"] = row["id"]
            # VULN #13 - Open Redirect: next_url used with ZERO validation
            if next_url:
                return redirect(next_url)
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error, next_url=next_url)


@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        conn = get_conn()
        cur = conn.cursor()
        # Registration IS parameterized (shown as a contrast point for students)
        cur.execute(
            "INSERT INTO users (username, password, email, role, secret_note) VALUES (?, ?, ?, 'user', '')",
            (username, password, email),
        )
        conn.commit()
        conn.close()
        message = "Registered! You can now log in."
    return render_template("register.html", message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# VULN #6 - SERVER-SIDE REQUEST FORGERY (SSRF)
# "Set avatar from URL" feature fetches whatever URL the user supplies, from
# the SERVER, with no validation on scheme/host/IP range. Can be used to
# probe internal services, cloud metadata endpoints, or localhost-only ports.
# Demo payload: http://127.0.0.1:5000/healthz  (reach an internal endpoint)
# Demo payload: http://169.254.169.254/latest/meta-data/  (cloud metadata, if on cloud VM)
# ---------------------------------------------------------------------------
@app.route("/avatar", methods=["GET", "POST"])
def avatar():
    if "username" not in session:
        return redirect(url_for("login"))
    result = None
    url = ""
    if request.method == "POST":
        url = request.form.get("url", "")
        try:
            # INTENTIONALLY VULNERABLE: no scheme/host/IP allow-list,
            # server happily fetches internal/private addresses too.
            resp = requests.get(url, timeout=5)
            result = f"Status: {resp.status_code}\n\n{resp.text[:2000]}"
        except Exception as e:
            result = f"Error: {e}"
    return render_template("avatar.html", result=result, url=url)


# ---------------------------------------------------------------------------
# VULN #4 - DOM-BASED XSS
# welcome.html reads location.hash on the CLIENT and injects it into the
# page via innerHTML with no sanitization. Never touches the server, so
# server-side filters/WAFs won't catch it.
# Demo URL: /welcome#<img src=x onerror=alert('dom-xss')>
# ---------------------------------------------------------------------------
@app.route("/welcome")
def welcome():
    return render_template("welcome.html")


# ---------------------------------------------------------------------------
# VULN #2 - REFLECTED XSS (search box echoes raw user input into HTML)
# Demo payload: <script>alert(document.cookie)</script>
# ---------------------------------------------------------------------------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{q}%",))
    results = cur.fetchall()
    conn.close()
    # `q` is passed to the template and rendered WITHOUT autoescape bypassed
    # intentionally via |safe filter inside search.html to demonstrate reflected XSS.
    return render_template("search.html", query=q, results=results)


# ---------------------------------------------------------------------------
# VULN #3 - STORED XSS (comment box, rendered with |safe in template)
# Demo payload: <img src=x onerror=alert('stored-xss')>
# ---------------------------------------------------------------------------
@app.route("/comments", methods=["GET", "POST"])
def comments():
    conn = get_conn()
    cur = conn.cursor()
    if request.method == "POST":
        username = session.get("username", "anonymous")
        comment = request.form.get("comment", "")
        cur.execute("INSERT INTO comments (username, comment) VALUES (?, ?)", (username, comment))
        conn.commit()
    cur.execute("SELECT * FROM comments ORDER BY id DESC")
    all_comments = cur.fetchall()
    conn.close()
    return render_template("comments.html", comments=all_comments, user=session.get("username"))


# ---------------------------------------------------------------------------
# VULN #4 - OS COMMAND INJECTION (network diagnostic tool)
# Demo payload (host field): 127.0.0.1; whoami
# Demo payload (host field): 127.0.0.1 && cat /etc/passwd
# ---------------------------------------------------------------------------
@app.route("/ping", methods=["GET", "POST"])
def ping():
    output = None
    host = ""
    if request.method == "POST":
        host = request.form.get("host", "")
        # INTENTIONALLY VULNERABLE: shell=True with unsanitized user input
        try:
            output = subprocess.check_output(
                f"ping -c 1 {host}", shell=True, stderr=subprocess.STDOUT, timeout=5
            ).decode(errors="replace")
        except Exception as e:
            output = str(e)
    return render_template("ping.html", output=output, host=host)


# ---------------------------------------------------------------------------
# VULN #7 - IDOR (Insecure Direct Object Reference)
# Any logged-in user can view ANY user's profile/secret note by changing
# the numeric id in the URL — no ownership check.
# Demo: log in as 'pawan' then browse /profile/1 to read admin's secret_note
# ---------------------------------------------------------------------------
@app.route("/profile/<int:user_id>")
def profile(user_id):
    if "username" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor()
    # No check that user_id == session['user_id'] -> IDOR
    cur.execute("SELECT id, username, email, role, secret_note FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "User not found", 404
    return render_template("profile.html", profile=row)


# ---------------------------------------------------------------------------
# VULN #8 - BROKEN ACCESS CONTROL (admin panel reachable without real
# authorization check — only checks a client-controlled session value and
# a hidden form field is trusted blindly on another endpoint below)
# ---------------------------------------------------------------------------
@app.route("/admin")
def admin_panel():
    # Deliberately weak check: trusts session['role'] which, combined with
    # VULN below (role is settable at registration via tampered POST),
    # can be escalated.
    if session.get("role") != "admin":
        return render_template("admin.html", authorized=False, users=None)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template("admin.html", authorized=True, users=users)


# ---------------------------------------------------------------------------
# VULN #9 - PRIVILEGE ESCALATION via mass-assignment style trust
# VULN #10 - CSRF: no CSRF token on this state-changing form; an attacker
# page can auto-submit this exact form cross-site using the victim's cookies.
# This endpoint trusts a hidden "role" field from the client when updating
# a profile — a user can tamper the form and promote themselves to admin.
# Demo: in browser devtools, edit the hidden <input name="role"> value to
# "admin" before submitting the form on /profile/edit
# ---------------------------------------------------------------------------
@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if "username" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor()
    if request.method == "POST":
        email = request.form.get("email", "")
        role = request.form.get("role", "user")  # trusted blindly (intentional)
        cur.execute(
            "UPDATE users SET email = ?, role = ? WHERE id = ?",
            (email, role, session["user_id"]),
        )
        conn.commit()
        session["role"] = role
    cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    row = cur.fetchone()
    conn.close()
    return render_template("edit_profile.html", profile=row)


# ---------------------------------------------------------------------------
# VULN #11 - INSECURE FILE UPLOAD (no extension/type/size validation,
# files served back directly -> can upload a .html/.svg with embedded JS,
# or in a misconfigured server, a script file)
#
# VULN #12 - PATH TRAVERSAL (filename used as-is, '..' not stripped).
# Demo: upload a file picked via a renamed path containing traversal, or
# craft a raw multipart POST (Burp Repeater) with
#   Content-Disposition: form-data; name="file"; filename="../../app.py"
# to write OUTSIDE the uploads/ folder -- can overwrite real app files.
# ---------------------------------------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    message = None
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            # No extension whitelist, no content-type check, no size limit.
            # filename used AS-IS with no secure_filename()/sanitization,
            # so '../' sequences escape the uploads/ directory entirely.
            save_path = os.path.join(UPLOAD_DIR, f.filename)
            f.save(save_path)
            message = f"Uploaded: {f.filename}"
    files = os.listdir(UPLOAD_DIR)
    return render_template("upload.html", message=message, files=files)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Served without re-checking type -> stored XSS via uploaded HTML/SVG possible
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------------------
# Sanity / health check for Jenkins + Docker HEALTHCHECK
# ---------------------------------------------------------------------------
@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
