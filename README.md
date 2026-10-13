# VulnLab — Intentionally Vulnerable Training Web App

Ye ek **deliberately insecure** Flask web app hai, jo cybersecurity training
sessions mein live pentesting demo ke liye banaya gaya hai (OWASP Top 10
style vulnerabilities). Isko Jenkins pipeline se Docker container ke roop
mein deploy kar sakte ho aur students ko real-time attack dikha sakte ho.

> ⚠️ **ISOLATION ZARURI HAI**: Is app ko kabhi bhi public internet par ya
> shared/production network par deploy mat karo. Sirf isolated lab VM,
> sandboxed Docker network, ya ek alag VLAN par chalao jahan sirf students
> access kar sakein.

---

## 📁 Project Structure

```
pentest-lab/
├── app.py                 # Main Flask app — all intentional vulnerabilities here
├── database.py             # SQLite seed data (plaintext passwords, demo users)
├── requirements.txt        # Python dependencies
├── Dockerfile               # Container build (installs ping utility too)
├── docker-compose.yml       # Local isolated-network run
├── Jenkinsfile               # CI/CD pipeline: build -> SAST -> secret scan -> container scan -> deploy
├── DEVOPS_CLOUD_GUIDE.md     # Project explained from Cloud & DevOps subject angle
├── VULNERABILITIES.md        # Full exploitation walkthrough for the demo
├── terraform/
│   └── main.tf                # IaC example — provisions an isolated AWS lab VM
├── templates/                # Jinja2 HTML templates
│   ├── base.html, index.html, login.html, register.html
│   ├── search.html, comments.html, ping.html
│   ├── profile.html, edit_profile.html, admin.html, upload.html
├── static/
│   └── style.css
└── uploads/                  # Runtime folder for uploaded files
```

---

## 🚀 Quick Start (Local, No Jenkins)

```bash
cd pentest-lab
pip install -r requirements.txt
python app.py
```
App chalegi: **http://localhost:5000**

Seed login users (see `database.py`): `admin / Admin@123`, `pawan / pawan123`,
`riya / riya2024`, `test / test`.

---

## 🐳 Run with Docker / docker-compose

```bash
docker-compose up --build
```
App: **http://localhost:5000**

---

## 🔧 Jenkins Deployment (Pipeline as Code)

1. Is poora `pentest-lab/` folder ek Git repo mein push karo (GitHub/GitLab/
   local Gitea — jo bhi Jenkins access kar sake).
2. Jenkins mein: **New Item → Pipeline**
3. Pipeline config mein: **Pipeline script from SCM → Git → apna repo URL**,
   script path `Jenkinsfile` (root mein hi hai, default sahi hai).
4. Jenkins agent par Docker installed hona chahiye aur jenkins user docker
   group mein hona chahiye:
   ```bash
   sudo usermod -aG docker jenkins
   sudo systemctl restart jenkins
   ```
5. **Build Now** daba do. Pipeline ye karegi:
   - Docker image build
   - `bandit` SAST scan chalayegi aur report archive karegi (students ko
     dikhane ke liye ki automated scanners bhi in vulnerabilities ko pakad
     lete hain)
   - Purana container hata kar naya deploy karegi
   - `/healthz` par smoke test karegi
6. Build complete hone ke baad app live hogi: `http://<jenkins-host>:5000/`

### Jenkins port note
Agar Jenkins khud port 5000 use kar raha hai ya conflict hai, to Jenkinsfile
mein `APP_PORT` environment variable change kar do.

---

## 🎯 What to Demo (summary — full steps + live fixes in VULNERABILITIES.md)

| # | Vulnerability | Where | Quick Payload |
|---|---|---|---|
| 1 | SQL Injection | `/login` | `admin' --` |
| 2 | Reflected XSS | `/search?q=` | `<script>alert(document.cookie)</script>` |
| 3 | Stored XSS | `/comments` | `<img src=x onerror=alert('xss')>` |
| 4 | DOM-Based XSS | `/welcome#` | `<img src=x onerror=alert('dom-xss')>` |
| 5 | OS Command Injection | `/ping` | `127.0.0.1; whoami` |
| 6 | SSRF | `/avatar` | `http://127.0.0.1:5000/healthz` |
| 7 | IDOR | `/profile/<id>` | Change id in URL while logged in as non-admin |
| 8 | Broken Access Control | `/admin` | Reach it after escalating role (#9) |
| 9 | Privilege Escalation | `/profile/edit` | Tamper hidden `role` field in devtools |
| 10 | CSRF | `/profile/edit` | Open `csrf_demo/csrf_poc.html` while logged in |
| 11 | Insecure File Upload | `/upload` | Upload `.html` with embedded `<script>` |
| 12 | Path Traversal | `/upload` | Burp: `filename="../../app.py"` |
| 13 | Open Redirect | `/login?next=` | `?next=https://evil-phish.example` |
| 14 | Session Fixation | login flow | Cookie unchanged before/after login |
| 15 | Insecure Cookie Flags | session cookie | Check DevTools: no `HttpOnly`/`SameSite` |
| 16 | No Rate Limiting | `/login` | Unlimited brute-force attempts |
| 17 | Sensitive Data Exposure | `vulnapp.db` | Plaintext passwords stored |
| 18 | Security Misconfiguration | any error page | `debug=True` leaks stack trace + raw SQL |
| 19 | Missing Security Headers | any page | Embed in `<iframe>` — no `X-Frame-Options` |
| 20 | Hardcoded Secret Key | `app.py` | Forge admin cookie with `flask-unsign` |

Full step-by-step class script — exploit, root cause, and **live-editable
fix code for each of the 20** — is in **VULNERABILITIES.md**.

---

## ☁️ Teaching this as a Cloud & DevOps Subject

Agar tumhara focus **Cloud and DevOps** subject hai (pentesting sirf
use-case hai), to **DEVOPS_CLOUD_GUIDE.md** dekho — wahan pura mapping hai:
CI/CD pipeline concepts, containerization, DevSecOps gates (SAST/secret
scan/container scan — jo ab Jenkinsfile mein hain), Infrastructure as Code
(`terraform/main.tf`), cloud deployment models (IaaS/PaaS/Containers), aur
monitoring/observability — sab is hi project se map kiya hua hai, with a
suggested 2-hour class flow.

---

## 🧯 Resetting the Lab

Database auto-recreates agar `vulnapp.db` delete kar do (restart par
automatically seed ho jayega):
```bash
docker exec -it vulnlab_target rm -f /app/vulnapp.db
docker restart vulnlab_target
```

---

## ⚖️ Responsible Use

Ye app sirf authorized training/educational environments ke liye hai.
Students ko clearly brief karo ki ye techniques sirf is lab app par hi
try karni hain — kisi real/production system par nahi, bina explicit
written authorization ke.
