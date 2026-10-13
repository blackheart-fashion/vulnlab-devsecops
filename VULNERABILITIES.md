# VulnLab — 20 Vulnerabilities: Exploit → Fix (Live Classroom Guide)

Is guide ko session ke script ki tarah use karo. Har vulnerability ke liye
teen cheezein hain:
1. **Exploit** — bacchon ko live dikhao kaise attack karte hain
2. **Root cause** — `app.py` mein exact kahan problem hai
3. **Fix** — line jo tum live edit karke `app.py` mein daal sakte ho, fir app
   restart karke dikhao ki exploit ab kaam nahi karta

**Recommended flow per vuln:** Exploit dikhao → Root cause explain karo →
Fix code paste karo → `docker restart vulnlab_target` (ya local run restart)
→ exploit dobara try karo → dikhao ki ab block ho gaya hai.

---

## 1. SQL Injection — Authentication Bypass (`/login`)

**Exploit:** Username field mein `admin' --` daalo, password kuch bhi. Query
comment ho jati hai, login bina password check ke ho jata hai.

**Root cause:**
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**Fix (live edit karo):**
```python
cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
row = cur.fetchone()
```
Parameterized query — ab `'` koi special meaning nahi rakhta.

---

## 2. Reflected XSS (`/search`)

**Exploit:** `http://localhost:5000/search?q=<script>alert(document.cookie)</script>`

**Root cause (`search.html`):**
```html
<p>Results for: {{ query|safe }}</p>
```

**Fix:** `|safe` filter hata do:
```html
<p>Results for: {{ query }}</p>
```
Jinja2 by default auto-escape karta hai — `|safe` hi vulnerability create kar raha tha.

---

## 3. Stored XSS (`/comments`)

**Exploit:** Comment box mein `<img src=x onerror=alert('stored-xss')>` daalo —
har user jo page kholega uske liye bhi trigger hoga.

**Root cause (`comments.html`):**
```html
<p>{{ c['comment']|safe }}</p>
```

**Fix:**
```html
<p>{{ c['comment'] }}</p>
```

---

## 4. DOM-Based XSS (`/welcome`)

**Exploit:** `http://localhost:5000/welcome#<img src=x onerror=alert('dom-xss')>`
Server ko kabhi pata hi nahi chalta — purely client-side attack.

**Root cause (`welcome.html` script):**
```javascript
document.getElementById('greeting').innerHTML = "Hello, " + hash + "!";
```

**Fix:** `innerHTML` ki jagah `textContent` use karo (HTML parse hi nahi hoga):
```javascript
document.getElementById('greeting').textContent = "Hello, " + hash + "!";
```

---

## 5. OS Command Injection (`/ping`)

**Exploit:** Host field mein `127.0.0.1; whoami` ya `127.0.0.1 && cat /etc/passwd`

**Root cause:**
```python
subprocess.check_output(f"ping -c 1 {host}", shell=True, ...)
```

**Fix:**
```python
import re
if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
    output = "Invalid host"
else:
    output = subprocess.check_output(
        ["ping", "-c", "1", host], shell=False, stderr=subprocess.STDOUT, timeout=5
    ).decode(errors="replace")
```
`shell=False` + argument list + input whitelist — teeno zaroori hain.

---

## 6. Server-Side Request Forgery / SSRF (`/avatar`)

**Exploit:** URL field mein `http://127.0.0.1:5000/healthz` daalo — server
khud apne internal endpoint ko hit karta hai. Cloud VM par
`http://169.254.169.254/latest/meta-data/` try karo (agar AWS/Azure/GCP par
hosted ho) — credentials leak ho sakte hain.

**Root cause:**
```python
resp = requests.get(url, timeout=5)  # no validation at all
```

**Fix:** URL ko allow-list/block-list se validate karo (private IP ranges block karo):
```python
import ipaddress, socket
from urllib.parse import urlparse

def is_safe_url(url):
    try:
        host = urlparse(url).hostname
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except Exception:
        return False

if not is_safe_url(url):
    result = "Blocked: internal/private addresses not allowed"
else:
    resp = requests.get(url, timeout=5)
```

---

## 7. IDOR — Insecure Direct Object Reference (`/profile/<id>`)

**Exploit:** `pawan` se login karo, phir `/profile/1` kholo — admin ka
`secret_note` dikh jayega, koi ownership check nahi hai.

**Root cause:**
```python
cur.execute("SELECT ... FROM users WHERE id = ?", (user_id,))
# user_id session se compare hi nahi hota
```

**Fix:**
```python
if user_id != session["user_id"] and session.get("role") != "admin":
    return "Forbidden", 403
```

---

## 8. Broken Access Control (`/admin`)

Point #9 (privilege escalation) ka continuation — escalate karne ke baad
admin panel access mil jata hai.

**Fix:** Role ko database-verified server-side source se hi check karo (see
fix #9), session value par blindly depend mat karo:
```python
cur.execute("SELECT role FROM users WHERE id = ?", (session.get("user_id"),))
current_role = cur.fetchone()
if not current_role or current_role["role"] != "admin":
    return render_template("admin.html", authorized=False, users=None)
```

---

## 9. Privilege Escalation via Hidden Field (`/profile/edit`)

**Exploit:** Login karo, `/profile/edit` kholo, DevTools (F12) se hidden
`<input name="role">` ki value `admin` kar do, submit karo, `/admin` kholo.

**Root cause:**
```python
role = request.form.get("role", "user")  # client se blindly trust
```

**Fix:** Role field ko form se bilkul accept hi mat karo:
```python
cur.execute("UPDATE users SET email = ? WHERE id = ?", (email, session["user_id"]))
# role update ek separate, admin-only endpoint se ho, user khud apna role kabhi na set kare
```

---

## 10. CSRF — Cross-Site Request Forgery (`/profile/edit`, `/comments`)

**Exploit:** `csrf_demo/csrf_poc.html` file browser mein open karo (ek alag
tab mein VulnLab login session active hona chahiye) — ye auto-submit hoke
victim ka role silently `admin` kar deta hai, bina unki marzi ke.

**Root cause:** Koi CSRF token hi nahi hai kisi bhi state-changing form mein,
aur `SESSION_COOKIE_SAMESITE = None` hai.

**Fix (Flask-WTF se CSRF protection, sabse simple way):**
```python
# requirements.txt mein add: Flask-WTF==1.2.1
from flask_wtf import CSRFProtect
csrf = CSRFProtect(app)
```
Har form mein add karo:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```
Plus cookie fix:
```python
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
```

---

## 11. Insecure File Upload (`/upload`)

**Exploit:** Ek `.html` file banao with `<script>alert('xss')</script>`,
upload karo, uploaded link kholo — script execute ho jata hai.

**Root cause:** Koi extension/content-type whitelist nahi hai.

**Fix:**
```python
ALLOWED_EXT = {"jpg", "jpeg", "png", "gif"}
ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
if ext not in ALLOWED_EXT:
    message = "File type not allowed"
else:
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(f.filename)
    f.save(os.path.join(UPLOAD_DIR, safe_name))
```

---

## 12. Path Traversal (`/upload`)

**Exploit:** Burp Repeater se raw multipart request bhejo jisme
`filename="../../app.py"` ho — upload folder ke bahar file overwrite ho
sakti hai.

**Root cause:** `f.filename` ko bina sanitize kiye directly use kiya jata hai.

**Fix:** (Fix #11 ka `secure_filename()` ye bhi automatically fix kar deta
hai — `../` sequences strip ho jate hain.)

---

## 13. Open Redirect (`/login?next=`)

**Exploit:** `http://localhost:5000/login?next=https://evil-phish.example`
par victim ko bhejo — valid login ke baad silently evil site par redirect
ho jata hai (phishing combo ke liye perfect).

**Root cause:**
```python
if next_url:
    return redirect(next_url)  # no validation
```

**Fix:** Sirf relative/internal paths allow karo:
```python
from urllib.parse import urlparse
if next_url and urlparse(next_url).netloc == "":
    return redirect(next_url)
return redirect(url_for("index"))
```

---

## 14. Session Fixation (login flow)

**Exploit:** Login se pehle ka session cookie note karo, login karo, dikhao
ki same cookie continue chal raha hai (regenerate nahi hua).

**Root cause:** Flask session ko login ke time explicitly reset/regenerate
nahi kiya jata.

**Fix:** Login success par session clear karke naya banao:
```python
session.clear()
session["username"] = row["username"]
session["role"] = row["role"]
session["user_id"] = row["id"]
```

---

## 15. Insecure Cookie Flags

**Exploit:** Browser DevTools → Application → Cookies kholo, dikhao ki
`HttpOnly` aur `SameSite` flags missing/off hain — matlab JS (XSS ke through)
session cookie steal kar sakta hai, aur cross-site requests mein bhi cookie
jaata hai.

**Root cause:**
```python
app.config["SESSION_COOKIE_HTTPONLY"] = False
app.config["SESSION_COOKIE_SAMESITE"] = None
```

**Fix:**
```python
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True  # HTTPS deploy mein
```

---

## 16. No Rate Limiting / Brute Force (`/login`)

**Exploit:** Burp Intruder ya simple script se `/login` par sainkdo password
guesses chalao — koi lockout/delay nahi hai.

**Root cause:** Login route mein koi attempt-counter nahi hai.

**Fix (simple in-memory version for demo):**
```python
from collections import defaultdict
import time
login_attempts = defaultdict(list)

# login() route ke andar, POST handling se pehle:
ip = request.remote_addr
now = time.time()
login_attempts[ip] = [t for t in login_attempts[ip] if now - t < 60]
if len(login_attempts[ip]) >= 5:
    return render_template("login.html", error="Too many attempts, try again later")
login_attempts[ip].append(now)
```
(Production mein `Flask-Limiter` library use karna better hai.)

---

## 17. Sensitive Data Exposure — Plaintext Passwords

**Exploit:** `vulnapp.db` ko DB Browser for SQLite se kholo, `users` table
dikhao — passwords plaintext mein hain.

**Root cause (`database.py`):** Passwords bina hashing ke store hote hain.

**Fix:**
```python
# requirements.txt mein add: bcrypt==4.2.0
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
# login verify time par:
bcrypt.checkpw(password.encode(), stored_hash)
```

---

## 18. Security Misconfiguration — Debug Mode + Verbose Errors

**Exploit:** Login mein ek malformed SQLi payload do jo query break kar de —
raw SQL query + DB error client ko dikh jayega.

**Root cause:**
```python
app.config["DEBUG"] = True
return render_template("login.html", error=f"DB error: {e} | Query: {query}")
```

**Fix:**
```python
app.config["DEBUG"] = False
return render_template("login.html", error="Invalid credentials")
# aur actual error ko server-side log karo: app.logger.error(str(e))
```

---

## 19. Missing Security Headers — Clickjacking

**Exploit:** Ek simple HTML file banao jisme VulnLab `<iframe>` mein embed
ho — dikhao ki browser allow kar deta hai (koi `X-Frame-Options` nahi hai):
```html
<iframe src="http://localhost:5000/admin" width="800" height="600"></iframe>
```

**Root cause:** Flask by default koi security headers add nahi karta.

**Fix:**
```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## 20. Hardcoded / Weak Secret Key

**Exploit:** Source code mein secret key dikhao (`super-secret-key-123`).
Tool **flask-unsign** se dikhao ki is known key se koi bhi apna khud ka
signed session cookie forge kar sakta hai (role=admin wala), bina login kiye:
```bash
pip install flask-unsign
flask-unsign --sign --cookie "{'role': 'admin', 'user_id': 1, 'username': 'admin'}" --secret 'super-secret-key-123'
```
Iska output cookie browser mein paste karo — seedha admin ban jaoge, login
kiye bina.

**Root cause:**
```python
app.config["SECRET_KEY"] = "super-secret-key-123"
```

**Fix:** Random, environment-variable-based secret:
```python
import secrets
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
```
(Production mein ye env variable se hi aana chahiye, kabhi code mein hardcode nahi.)

---

## Suggested 2-Hour Class Flow

| Time | Vulns Covered |
|---|---|
| 0:00–0:15 | App overview, architecture, Jenkins pipeline recap |
| 0:15–0:35 | #1 SQLi, #17 Plaintext passwords, #20 Secret key forge |
| 0:35–0:55 | #2, #3, #4 — Reflected/Stored/DOM XSS |
| 0:55–1:10 | #5 Command Injection, #6 SSRF |
| 1:10–1:35 | #7, #8, #9, #10 — IDOR → Priv Esc → Admin access → CSRF chain |
| 1:35–1:50 | #11, #12 File Upload + Path Traversal |
| 1:50–2:00 | #13, #14, #15, #16, #18, #19 — quick-fire rest, live-fix demo on 2-3 of them |

## Tooling Students Should Have Ready

- **Burp Suite Community / OWASP ZAP** — intercept, tamper, Intruder (#16),
  Repeater (#12)
- **sqlmap** — automated SQLi discovery against `/login`
- **flask-unsign** — secret key / cookie forgery demo (#20)
- Browser DevTools — hidden fields, cookies, console
- `curl` / Postman — manual request crafting

## Resetting the Lab Between Demos

```bash
docker exec -it vulnlab_target rm -f /app/vulnapp.db
docker restart vulnlab_target
```

## ⚖️ Responsible Use

Sirf authorized training/educational environments ke liye. Students ko clear
brief do ki ye techniques sirf lab app par try karni hain, kisi real/production
system par nahi, bina explicit written authorization ke.
