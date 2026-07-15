# AllExpense — Personal Finance Dashboard

> A family expense tracker built as a full DevOps learning project — live in production at **[allexpense.me](https://allexpense.me)**

---

## What it does

A real app used daily by Ido and his family. Track expenses, set budgets, scan receipts, and see where money goes — all from any device including phone.

**Key features:**
- Add expenses manually or scan a receipt (Claude AI fills the form automatically)
- Monthly budget per category with progress bars
- Donut chart breakdown by category
- Standing orders tracking
- Shared expense pools (invite family members)
- Live USD / EUR exchange rates — historical rate locked at time of entry
- Hebrew / English support throughout
- Export to Excel / CSV
- Fully responsive mobile layout

---

## Architecture

```
                         ┌─────────────────────────────────────────┐
                         │              GitHub                      │
                         │   git push → GitHub Actions triggers     │
                         └────────────────┬────────────────────────┘
                                          │
              ┌───────────────────────────▼───────────────────────────┐
              │                  CI/CD Pipeline                        │
              │  test → build → ECR push → Trivy scan → ArgoCD patch  │
              └───────────────────────────┬───────────────────────────┘
                                          │
                         ┌────────────────▼────────────────┐
                         │         AWS EC2 (t3.medium)      │
                         │         k3s Kubernetes cluster   │
                         │                                  │
                         │  ┌─────────┐  ┌──────────────┐  │
                         │  │ Backend │  │  PostgreSQL   │  │
                         │  │  Flask  │  │  (PVC)        │  │
                         │  └─────────┘  └──────────────┘  │
                         │  ┌──────────────────────────┐    │
                         │  │  Prometheus + Grafana     │    │
                         │  │  (monitoring namespace)   │    │
                         │  └──────────────────────────┘    │
                         │  ┌──────────────────────────┐    │
                         │  │  ArgoCD (GitOps sync)    │    │
                         │  └──────────────────────────┘    │
                         │  Traefik ingress + TLS (Let's    │
                         │  Encrypt via cert-manager)        │
                         └─────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Backend | Python / Flask | REST API — expenses, auth, receipt scanning |
| Frontend | HTML / CSS / JavaScript | Single-page app, Chart.js |
| Database | PostgreSQL 16 | Persistent storage |
| Containers | Docker | Packages the app |
| Orchestration | Kubernetes (k3s) | Runs everything in a cluster on EC2 |
| Helm | Helm chart | Packages K8s manifests for easy deploy |
| IaC | Terraform | EC2, ECR, IAM, Elastic IP, S3 state backend |
| CI/CD | GitHub Actions | test → build → push → security scan → deploy |
| Registry | AWS ECR | Docker image storage (immutable tags) |
| GitOps | ArgoCD | Watches Git, syncs new image tags to cluster |
| Monitoring | Prometheus + Grafana | Metrics scraping and dashboards |
| HTTPS | cert-manager + Let's Encrypt | Auto-renewing TLS certificate |
| Auth | JWT + bcrypt | Secure login, multi-user, shared pools |
| AI | Claude Haiku (vision) | Receipt scanning → auto-fill expense form |

---

## CI/CD Flow

One `git push` to `main` triggers the full pipeline:

```
git push
  → 1. Run pytest tests
  → 2. Build Docker image, push to ECR tagged with git SHA
  → 3. Trivy security scan (CRITICAL severity, ignore unfixed)
  → 4. Patch ArgoCD application image tag → ArgoCD syncs → rollout waits
```

ECR credentials on the cluster auto-refresh every 6 hours via a K8s CronJob.

---

## Infrastructure (Terraform)

```
terraform/
├── main.tf       — provider, S3 backend (finance-dashboard-tfstate-*)
├── ec2.tf        — EC2 t3.medium, Elastic IP, security group
├── budget.tf     — AWS Budget alert at $10/month
└── variables.tf  — admin_cidr_blocks, anthropic_api_key (gitignored tfvars)
```

State stored in S3 with DynamoDB lock. ECR has immutable tags and a lifecycle policy (keep last 10 images).

---

## Project Structure

```
finance-dashboard/
├── backend/
│   ├── app.py            — Flask API (expenses, auth, pools, receipt scan)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html        — Main app (dashboard, expenses, budgets)
│   ├── login.html        — Auth page
│   └── style.css
├── finance-chart/        — Helm chart
│   └── templates/        — K8s manifests (deployment, service, ingress, PVC, CronJob)
├── terraform/            — IaC for AWS resources
├── scripts/
│   └── health-check.sh   — Checks pods, endpoints, ingress
├── .github/workflows/
│   └── deploy.yml        — Full CI/CD pipeline
└── docker-compose.yml    — Local development
```

---

## Run Locally

```bash
git clone https://github.com/idofurman/finance-dashboard.git
cd finance-dashboard

# Start backend + PostgreSQL
docker-compose up --build

# App runs at http://localhost:5000
```

---

## Kubernetes (k3s on EC2)

```bash
# Check running pods
kubectl get pods

# View logs
kubectl logs -l app=backend -f

# Health check
bash scripts/health-check.sh
```

---

## Security

- Secrets stored as Kubernetes secrets (never in Git)
- Git history scrubbed with `git-filter-repo` (API key incident)
- ECR: immutable image tags + lifecycle policy
- CORS restricted to `https://allexpense.me`
- Trivy scan on every deploy (blocks on CRITICAL unfixed CVEs)
- Branch protection on `main` (PRs required, tests must pass)

---

## Monitoring

Prometheus scrapes Flask `/metrics` endpoint. Grafana dashboards on the cluster show request rate, latency, and pod health.

```bash
# Port-forward Grafana locally
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

---

## Extra Features (beyond academy requirements)

- **Receipt scanner** — photo → Claude Haiku vision API → auto-fills expense form
- **Exchange rates** — live USD/EUR from API, historical rate locked at entry time
- **Shared pools** — invite family members, shared expense groups with invite/accept/decline flow
- **Hebrew/English i18n** — full translation throughout the UI
- **Mobile-first** — fully responsive layout, same design on phone and desktop
- **Excel/CSV export** — download expense history
- **Custom month picker** — popup calendar translated in both languages
