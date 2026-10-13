# VulnLab — Cloud & DevOps Subject Perspective

Ye document VulnLab project ko **Cloud and DevOps subject ke syllabus** ke
hisaab se explain karta hai — har concept ka seedha mapping hai is project
ke kisi na kisi file/stage se. Pentesting sirf ek **use-case** hai; asli
seekhne wali cheez hai **poora DevOps pipeline + cloud deployment model**
kaise kaam karta hai, end to end.

---

## 1. Core Mapping: Subject Topics → Project Files

| DevOps/Cloud Concept | Is Project Mein Kahan | File |
|---|---|---|
| Source Control / VCS | Git repo jisme code push karte ho | (tumhara GitHub repo) |
| Continuous Integration (CI) | Checkout → Build → Scan stages | `Jenkinsfile` |
| Continuous Deployment (CD) | Deploy + Smoke Test stages | `Jenkinsfile` |
| Containerization | App ko container image mein package karna | `Dockerfile` |
| Container Orchestration (basic) | Container run/restart policy | `docker-compose.yml` |
| Infrastructure as Code (IaC) | Cloud VM declare karna code se | `terraform/main.tf` |
| DevSecOps (Shift-Left Security) | Pipeline ke andar security gates | `Jenkinsfile` (SAST/Secret/Container scan stages) |
| Configuration Management | Env vars, secrets handling | `app.py` (`SECRET_KEY`, vuln #20) |
| Monitoring / Observability | Health check endpoint | `/healthz` route in `app.py` |
| Cloud Networking & Security | VPC, Subnet, Security Group | `terraform/main.tf` |

---

## 2. CI/CD Pipeline — Concept Explanation

**CI (Continuous Integration)** = har code change ko automatically build +
test karna, taaki bugs jaldi pakde jayein.

**CD (Continuous Deployment/Delivery)** = tested code ko automatically
deploy karna, bina manual intervention ke.

`Jenkinsfile` mein pura pipeline declarative syntax mein likha hai
(`pipeline { stages { ... } }`). Har `stage` ek alag step hai jo sequentially
chalta hai:

```
Checkout → Build → SAST Scan → Secret Scan → Container Scan → Stop Old → Deploy → Smoke Test
```

**Class mein dikhane layak points:**
- Jenkins **Blue/Green indicator** — har stage pass/fail hone par green/red
  dikhata hai (Jenkins UI mein "Stage View")
- **"Pipeline as Code"** concept — ye pura workflow ek text file
  (`Jenkinsfile`) mein hai, Git mein version-controlled hai — koi bhi click-based
  manual config nahi
- Agar koi stage fail ho jaye (e.g. smoke test fail), pipeline turant ruk
  jati hai — ye "fail fast" principle demonstrate karta hai

---

## 3. Containerization — Docker Concepts

`Dockerfile` padhte waqt ye concepts cover karo:

| Dockerfile Line | Concept |
|---|---|
| `FROM python:3.11-slim` | **Base image** — layered filesystem ka foundation |
| `RUN apt-get install ...` | Har `RUN` ek naya **layer** banata hai (layer caching concept) |
| `COPY requirements.txt .` ← pehle, code baad mein | **Layer caching optimization** — dependencies change kam hoti hain, isliye unhe pehle copy karo taaki Docker cache reuse ho |
| `EXPOSE 5000` | Container kis port par listen karega (documentation, actual binding `-p` flag se hoti hai) |
| `HEALTHCHECK` | Container-level health monitoring — Docker khud restart kar sakta hai agar unhealthy ho |
| `CMD ["gunicorn", ...]` | Container start hote hi kya chalega |

**Class Exercise:** `docker build` karte waqt layer-by-layer output dikhao,
phir ek chhota sa code change karke dubara build karo — dikhao ki cached
layers skip ho jate hain (sirf changed layers rebuild hote hain). Ye real
CI/CD mein build speed ka bada factor hai.

**docker-compose.yml** se samjhao:
- **Orchestration basics** — multi-container apps (abhi single hai, lekin
  structure extend ho sakta hai database container add karne ke liye)
- **Networks** — isolated bridge network kyun zaroori hai (lab isolation)
- **Restart policies** — `unless-stopped` production-like reliability

---

## 4. DevSecOps — Security Pipeline Mein Integrated

Ye is project ka **sabse important teaching point** hai Cloud/DevOps subject
ke liye: security ko pipeline ke end mein nahi, **har stage mein** check karna.

### Gate 1: SAST (Static Application Security Testing) — `bandit`
Source code ko **bina run kiye** scan karta hai insecure patterns ke liye
(e.g. `subprocess` with `shell=True`, hardcoded secrets). Ye "shift-left"
hai — bug ko developer ke paas hi pakad lena, production mein jaane se pehle.

### Gate 2: Secret Scanning — `gitleaks`
Code/git history mein accidentally commit hui secrets (API keys, passwords,
`SECRET_KEY`) dhundta hai. Real companies mein ye stage **bohot critical**
hai — GitHub par daily hazaron leaked AWS keys scan hote hain bots se.

### Gate 3: Container Image Scanning — `trivy`
Built Docker image ke andar OS packages aur Python libraries mein **known
CVEs** (Common Vulnerabilities and Exposures) dhundta hai. Base image
(`python:3.11-slim`) purani ho sakti hai with known vulnerabilities — ye
tool wahi pakadta hai.

**Class Demo:** Build chalao, phir Jenkins mein **archived artifacts**
(`bandit-report.txt`, `gitleaks-report.json`, `trivy-report.txt`) kholo —
dikhao ki automated tools humari 20 mein se kayi vulnerabilities **khud hi
dhund leti hain** bina manual pentesting ke. Isse "Security as part of
pipeline, not an afterthought" wala concept clearly samajh aata hai.

---

## 5. Infrastructure as Code (IaC) — `terraform/main.tf`

Ye file dikhati hai ki cloud infrastructure (VM, network, firewall) ko
**code se declare** kaise karte hain, Console mein manually click karne ki
jagah.

**Key concepts to teach:**

| Terraform Block | Concept |
|---|---|
| `provider "aws"` | Kaunsa cloud provider (AWS/Azure/GCP — provider-agnostic concept) |
| `resource "aws_vpc"` | Isolated network banana — **cloud networking fundamentals** |
| `resource "aws_security_group"` | Cloud firewall — sirf zaroori ports/IPs allow karna |
| `variable "my_ip_cidr"` | **Parameterization** — hardcode values nahi, variables use karo |
| `user_data` | **Bootstrap script** — VM boot hote hi Docker+Jenkins auto-install ho jata hai |
| `output` | Deployment ke baad important values (IP, URLs) print karna |

**Class Exercise (agar AWS account available ho):**
```bash
cd terraform
terraform init      # providers download karta hai
terraform plan       # dikhata hai KYA banega, bina banaye
terraform apply       # actually resources create karta hai
terraform destroy      # sab clean delete kar deta hai (cost-saving demo!)
```
`terraform plan` ka output dikhana sabse important hai — students ko
samjhao ki IaC ka fayda ye hai ki tum **pehle se dekh sakte ho** kya change
hoga, bina kuch tod ke.

> ⚠️ Note: AMI ID aur region verify karna zaroori hai apply karne se pehle
> (AWS console mein current Ubuntu 22.04 AMI dhund lena). Cost-conscious
> rehna — `t3.medium` paisa leta hai, kaam hone ke baad turant `terraform
> destroy` chalana.

---

## 6. Cloud Deployment Models — Discussion Points

Is project ko base banakar class mein discuss karo:

- **IaaS (Infrastructure as a Service)** — jo humne Terraform se banaya
  (raw EC2 VM) — hum khud OS, Docker, Jenkins sab manage karte hain
- **PaaS (Platform as a Service)** — agar yahi app AWS Elastic Beanstalk ya
  Azure App Service par deploy karte, to underlying VM management hum nahi
  karte
- **Containers as a Service** — AWS ECS/Fargate, Azure Container Instances
  — sirf container image do, infra cloud manage karta hai
- **Kubernetes angle** — agar scale karna ho to ye hi Docker image ek
  Kubernetes Deployment + Service YAML mein wrap ho sakti hai (agle
  module ka topic ho sakta hai)

---

## 7. Monitoring & Observability

`/healthz` endpoint (`app.py`) aur `HEALTHCHECK` (`Dockerfile`) dikhate hain
**basic observability**:
- Docker khud container ko "unhealthy" mark kar sakta hai
- Jenkins ka **Smoke Test** stage deploy ke baad verify karta hai ki app
  actually response de rahi hai
- Real production mein isi concept ko Prometheus/Grafana/CloudWatch jaise
  tools se extend karte hain (alerting, dashboards, logs aggregation)

---

## 8. Suggested Class Flow — Cloud & DevOps Angle (2 Hours)

| Time | Topic | Reference |
|---|---|---|
| 0:00–0:15 | CI/CD concept intro, pipeline-as-code | `Jenkinsfile` walkthrough |
| 0:15–0:35 | Docker build live demo, layers, caching | `Dockerfile` |
| 0:35–0:55 | DevSecOps gates — run bandit/gitleaks/trivy live, dikhao reports | Jenkins archived artifacts |
| 0:55–1:15 | IaC concept, Terraform plan/apply walkthrough | `terraform/main.tf` |
| 1:15–1:35 | Cloud deployment models discussion (IaaS/PaaS/Containers/K8s) | Whiteboard discussion |
| 1:35–1:50 | Deploy pipeline end-to-end live run, dekho stage view | Jenkins UI |
| 1:50–2:00 | Monitoring/healthcheck concept, Q&A | `/healthz` demo |

**Optional add-on session:** Isi app ki 20 vulnerabilities ko **appsec**
angle se alag session mein cover karo (`VULNERABILITIES.md` use karo) — wo
DevSecOps ke "why we scan" wale reasoning ko reinforce karega.

---

## 9. Key Takeaway Statement for Students

> "DevOps sirf tools (Jenkins, Docker, Terraform) chalana nahi hai — ye ek
> **culture aur pipeline design philosophy** hai jahan code se leke
> production tak har step automated, repeatable, aur security-checked hota
> hai. Is lab mein tumne wahi pura cycle dekha: code commit → automated
> build → automated security scan → automated deploy → automated health
> check — sab ek click (`Build Now`) se."
