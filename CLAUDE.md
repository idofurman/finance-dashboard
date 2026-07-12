# CLAUDE.md — Finance Dashboard DevOps Project

## Who is the student?

- **Name:** Ido Furman (GitHub: idofurman)
- **Location:** Israel
- **Level:** Intermediate — comfortable with Linux CLI and Python basics, learning DevOps by building a real project
- **Learning style:** Needs deep understanding before execution. Always explain the WHY before the HOW. Never just give commands to copy-paste.

---

## How to teach Ido — strict rules

1. **Explain before executing** — before every command or file, explain what it does in plain language
2. **One small step at a time** — never give more than one concept at once
3. **Don't write code for him** — describe what needs to be done, let him write it, then review
4. **When he's stuck** — give a hint or explain the concept differently, not the answer
5. **When he makes a mistake** — point out exactly what's wrong and why, let him fix it
6. **Review every paste** — when he pastes code, review it carefully before moving on
7. **Celebrate progress** — when something works, acknowledge it and explain what just happened

---

## The project — Personal Finance Dashboard

A real family expense tracking app that Ido and his parents will actually use daily — not just a demo project. Built with a full DevOps infrastructure underneath.

### The real app vision
- **Users:** Ido + his parents (shared family app)
- **Priority 1:** Add expenses quickly from phone — mobile-first UI
- **Priority 2:** See where money is going — charts and breakdowns
- **Priority 3:** Set monthly budgets per category
- **Priority 4:** History and trends over time
- **Auto-import:** israeli-bank-scrapers to pull transactions automatically from Cal/Max/Isracard

### Expense categories
- 🛒 Groceries
- 🏠 Housing (rent, electricity, water)
- 🚗 Transport (gas, parking, insurance)
- 🍔 Food & restaurants
- 👕 Clothing
- 💊 Health
- 📱 Subscriptions
- 🎮 Entertainment
- 📚 Education
- 💰 Other

### App screens
- **Dashboard** — monthly summary, top categories, budget progress bars
- **Expenses list** — searchable, filterable, sortable table
- **Add expense** — fast mobile-friendly form
- **Budgets** — set monthly limit per category, see remaining
- **Trends** — month over month charts

### Build layers
- **Layer 1 (Week 2)** — real UI, manual entry, mobile-friendly, charts. Usable immediately.
- **Layer 2 (Week 4)** — bank scraping via israeli-bank-scrapers, automatic nightly imports
- **Layer 3 (post-course)** — user accounts, family login, per-user views

### App components

| Component | Technology | Purpose |
|---|---|---|
| Backend | Python / Flask | REST API for expenses |
| Frontend | HTML / CSS / JavaScript | Mobile-first UI with charts |
| Database | PostgreSQL | Permanent storage |
| Scraper | israeli-bank-scrapers (Node.js) | Auto-import from Israeli banks |

### Infrastructure

| Topic | Tool | What it does |
|---|---|---|
| Containers | Docker | Packages each component |
| Orchestration | Kubernetes (k3s) | Runs containers in a cluster |
| IaC | Terraform | Infrastructure as code |
| CI/CD | GitHub Actions | Auto test, build, deploy on git push |
| Registry | AWS ECR | Stores Docker images |
| GitOps | ArgoCD | Auto-syncs Git to Kubernetes |
| Monitoring | Prometheus + Grafana | Live dashboards and alerts |
| Scripting | Bash | Health checks, backups, automation |

### Repository
`github.com/idofurman/finance-dashboard`

### Dev environment
- Linux machine (Ubuntu)
- VS Code with Remote SSH
- k3s for local Kubernetes

---

## Progress tracker

### ✅ Week 1 — App + Docker (COMPLETE)

**What was built:**
- `backend/app.py` — Flask REST API with 3 endpoints: `/health`, GET `/expenses`, POST `/expenses`
- `backend/requirements.txt` — flask, flask-cors, psycopg2-binary
- `backend/Dockerfile` — python:3.12-slim base, installs deps, runs app
- `backend/.dockerignore` — excludes venv, pycache
- `docker-compose.yml` — backend + PostgreSQL services
- `.gitignore` — excludes venv, pycache, .env
- Pushed to GitHub via SSH key

**Key concepts learned:**
- REST API structure and HTTP methods
- Flask routes and decorators
- Docker image layers and Dockerfile instructions
- docker-compose services and networking
- Git workflow — init, add, commit, push
- SSH key authentication

---

### ✅ Week 2 — Kubernetes + IaC + Frontend (COMPLETE)

**Goal:** Deploy the app into a real Kubernetes cluster AND build a real usable frontend

**Steps to complete:**
1. ✅ Install k3s on Linux machine
2. ✅ Configure kubectl without sudo
3. ✅ Understand K8s core concepts (pods, deployments, services, PVC)
4. ✅ Write Deployment manifest for backend — `k8s/backend-deployment.yml`
5. ✅ Write Service manifest for backend — `k8s/backend-service.yml`
6. ✅ Write Deployment manifest for PostgreSQL — `k8s/db-deployment.yml`
7. ✅ Write Service manifest for PostgreSQL — `k8s/db-service.yml`
8. ✅ Write PersistentVolumeClaim for PostgreSQL — `k8s/db-pvc.yml`
9. ✅ Build Docker image — `finance-backend:latest`
10. ✅ Import image into k3s (`docker save` → `k3s ctr images import`)
11. ✅ Deploy everything with kubectl apply
12. ✅ Install Helm
13. ✅ Convert manifests into a Helm chart (`finance-chart/templates/`) — deployed via `helm install finance`
14. ✅ Build the real frontend (mobile-first, charts, add expense form)
15. ✅ Terraform — ECR, EC2 (t3.small), budget alerts, IAM role
16. ✅ Moved k3s to AWS EC2 (52.20.107.63) — real cloud deployment
17. ✅ Receipt scanner — `/parse-receipt` endpoint using Claude Haiku vision API

**Frontend to build:**
- Mobile-first responsive design
- Dashboard with spending summary and category breakdown (Chart.js)
- Expense list — searchable and filterable
- Add expense form — fast, works great on phone
- Budget progress bars per category
- Connects to Flask API via fetch()

**Key concepts to teach:**
- What is a node, pod, deployment, service
- Why K8s over docker-compose
- kubectl basic commands: get, describe, logs, apply, delete
- The difference between a Deployment and a Pod
- ClusterIP vs NodePort vs LoadBalancer services
- What Helm solves and why charts exist
- Responsive CSS — mobile-first design

---

### ✅ Week 3 — CI/CD Pipeline (COMPLETE)

**Goal:** One `git push` triggers test → build → push to ECR → deploy to k3s

**Steps:**
1. ✅ Write basic pytest tests for the Flask API
2. ✅ Create GitHub Actions workflow file
3. ✅ Set up AWS ECR repository
4. ✅ Configure GitHub secrets (AWS credentials, EC2 SSH key)
5. ✅ Pipeline stages: test → docker build → ECR push → deploy to EC2
6. ✅ Branch protection on main (PR required, tests must pass)

**Key concepts to teach:**
- What CI and CD mean separately
- GitHub Actions: workflows, jobs, steps, triggers
- What a container registry is and why ECR
- GitHub secrets — never hardcode credentials
- How the pipeline connects all the pieces

---

### 🔄 Week 4 — Monitoring + ArgoCD + Polish (IN PROGRESS / NEXT)

**Goal:** Observability, GitOps deployment, and demo-ready project

**Steps:**
1. Deploy Prometheus + Grafana into k3s
2. Add metrics endpoint to Flask app (`/metrics`)
3. Build Grafana dashboard
4. Set up 2 alert rules
5. Install ArgoCD
6. Configure ArgoCD to watch the GitHub repo
7. Write Bash health check scripts
8. Write README
9. Record demo video

**Bonus (if time allows):**
- Bank scraping via `israeli-bank-scrapers` — auto-import from Cal/Max/Isracard nightly via K8s CronJob
- Slack alert integration
- Note: israeli-bank-scrapers stores bank credentials on the server — acceptable for self-hosted family use

**Key concepts to teach:**
- The difference between logs, metrics, and traces
- What Prometheus scraping means
- Grafana datasources and panels
- What GitOps means and how ArgoCD implements it
- The difference between push-based and pull-based deployment

---

## Complete file reference

### `backend/app.py`
```python
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

expenses = [
    {"id": 1, "amount": 10, "category": "groceries"},
    {"id": 2, "amount": 150, "category": "bills"}
]

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

@app.route("/expenses", methods=["GET", "POST"])
def expenses_route():
    if request.method == "GET":
        return jsonify(expenses)
    elif request.method == "POST":
        new_expense = request.get_json()
        expenses.append(new_expense)
        return jsonify(new_expense), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### `backend/requirements.txt`
```
flask==3.0.3
flask-cors==4.0.1
psycopg2-binary==2.9.9
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "app.py"]
```

### `backend/.dockerignore`
```
venv
__pycache__
*.pyc
```

### `docker-compose.yml`
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://admin:secret@db:5432/finance

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: finance
```

### `.gitignore`
```
venv/
__pycache__/
*.pyc
.env
```

---

## Academy requirements checklist

| Requirement | Status | Notes |
|---|---|---|
| Git repository | ✅ Done | github.com/idofurman/finance-dashboard |
| Docker containers | ✅ Done | backend + db |
| Kubernetes deployment | ✅ Done | k3s on EC2 t3.small (52.20.107.63) |
| Helm chart | ✅ Done | finance-chart/, deployed via helm upgrade |
| Terraform | ✅ Done | ECR, EC2 t3.small, IAM, budget alerts |
| GitHub Actions CI/CD | ✅ Done | test → build → ECR push → deploy to EC2 |
| AWS ECR | ✅ Done | 579083551085.dkr.ecr.us-east-1.amazonaws.com/finance-backend |
| ArgoCD | ⏳ Week 4 | GitOps |
| Prometheus + Grafana | ⏳ Week 4 | monitoring |
| Bash scripts | ⏳ Week 4 | health checks |
| README + docs | ⏳ Week 4 | final polish |

---

## Demo day flow

```
git push
    → GitHub Actions triggers
    → Tests run
    → Docker image built and pushed to ECR
    → ArgoCD detects change in Git
    → New version deployed to k3s
    → Grafana shows the deployment live
```

One push. Every tool visible. That's the demo.
