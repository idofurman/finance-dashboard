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
                         +------------------------------------------+
                         |              GitHub                       |
                         |   git push -> GitHub Actions triggers     |
                         +--------------------+---------------------+
                                              |
              +-------------------------------v-----------------------+
              |                  CI/CD Pipeline                       |
              |  test -> build -> ECR push -> Trivy scan -> deploy    |
              +-------------------------------+-----------------------+
                                              |
                         +--------------------v--------------------+
                         |           AWS EKS (finance-eks)         |
                         |           us-east-1  /  2-3 nodes       |
                         |                                          |
                         |  +-----------+   +-----------+           |
                         |  | Backend   |   | Frontend  |           |
                         |  | Flask x2  |   | nginx x2  |           |
                         |  +-----------+   +-----------+           |
                         |  +-----------------------------------+   |
                         |  | PostgreSQL (EBS persistent volume)|   |
                         |  +-----------------------------------+   |
                         |  +-----------------------------------+   |
                         |  | ArgoCD  (GitOps sync)             |   |
                         |  +-----------------------------------+   |
                         |  +-----------------------------------+   |
                         |  | Prometheus + Grafana (monitoring) |   |
                         |  +-----------------------------------+   |
                         |  ingress-nginx + TLS (cert-manager / |   |
                         |  Let's Encrypt)                       |   |
                         +------------------------------------------+
                                              |
                         +--------------------v--------------------+
                         |       AWS Secrets Manager               |
                         |  DB credentials, JWT secret, API key    |
                         |  synced to cluster via ESO (IRSA auth)  |
                         +-----------------------------------------+
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Backend | Python / Flask | REST API — expenses, auth, receipt scanning |
| Frontend | HTML / CSS / JavaScript | Single-page app, Chart.js |
| Database | PostgreSQL 16 | Persistent storage on EBS volume |
| Containers | Docker (multistage) | Lean production images |
| Orchestration | Kubernetes (AWS EKS) | Managed cluster, 2-3 t3.medium nodes |
| Helm | Helm chart | Packages all K8s manifests |
| IaC | Terraform (modules) | VPC, EKS, ECR, DNS, S3 state backend |
| CI/CD | GitHub Actions | test -> build -> ECR push -> Trivy scan -> deploy |
| Registry | AWS ECR | Immutable image tags (SHA-based) |
| GitOps | ArgoCD | Watches Git, syncs image tags to cluster automatically |
| Secrets | ESO + AWS Secrets Manager | Secrets never in Git, synced via IRSA |
| Autoscaling | HPA + Cluster Autoscaler | Pods scale 2-5, nodes scale 2-3 |
| Resilience | PodDisruptionBudget | minAvailable: 1 on all deployments |
| Monitoring | Prometheus + Grafana | kube-prometheus-stack, metrics + dashboards |
| HTTPS | cert-manager + Let's Encrypt | Auto-renewing TLS via ingress-nginx |
| Auth | JWT + bcrypt | Secure login, multi-user, shared pools |
| AI | Claude Haiku (vision) | Receipt scanning -> auto-fill expense form |

---

## CI/CD Flow

One `git push` to `main` triggers the full pipeline:

```
git push
  -> 1. pytest — Flask API tests
  -> 2. Docker build (multistage), push both images to ECR with git SHA tag (immutable)
  -> 3. Trivy security scan — scans backend AND frontend, blocks on CRITICAL unfixed CVEs
  -> 4. kubectl patch ArgoCD application with new image tags
  -> 5. ArgoCD syncs Helm chart to EKS
  -> 6. kubectl rollout status -n default waits for all pods to be healthy
```

ECR authentication on the cluster is handled automatically by the EKS node IAM role — no credentials to rotate.

---

## Infrastructure (Terraform)

```
terraform/
├── main.tf                  — module wiring
├── providers.tf             — AWS, Kubernetes, Helm providers
├── variables.tf             — aws_region, environment, alert_email, etc.
├── locals.tf                — common tags applied to every resource
├── cluster-autoscaler.tf    — IRSA role + Helm release for cluster autoscaler
├── monitoring.tf            — Helm release for kube-prometheus-stack
├── budget.tf                — AWS Budget alert at $10/month
├── backend.tf               — S3 state backend + DynamoDB lock
└── modules/
    ├── vpc/                 — VPC, subnets, NAT gateway
    ├── eks/                 — EKS cluster + managed node group
    ├── ecr/                 — ECR repositories (immutable tags)
    ├── s3/                  — S3 buckets
    └── dns/                 — Route53 hosted zone + A record
```

State stored in S3 (`finance-dashboard-tfstate-579083551085`) with DynamoDB lock.

---

## Project Structure

```
finance-dashboard/
├── backend/
│   ├── app.py               — Flask API (expenses, auth, pools, receipt scan)
│   ├── Dockerfile           — multistage: builder installs deps, runtime copies venv
│   ├── test_app.py          — pytest tests (mock get_db + get_pool for CI)
│   └── requirements.txt
├── frontend/
│   ├── index.html           — Main app (dashboard, expenses, budgets, trends)
│   ├── login.html           — Auth page
│   ├── Dockerfile           — nginx:1.27-alpine + apk upgrade to patch base CVEs
│   └── nginx.conf           — gzip, server_tokens off, security headers, cache-control
├── finance-chart/           — Helm chart
│   ├── values.yaml          — image repos, storage class, ports
│   └── templates/
│       ├── backend-deployment.yml
│       ├── frontend-deployment.yml
│       ├── db-deployment.yml
│       ├── ingress.yml      — /api -> backend, / -> frontend
│       ├── secret-store.yml — ESO ClusterSecretStore (AWS Secrets Manager)
│       ├── external-secrets.yml — syncs db-credentials + finance-secrets
│       ├── backend-hpa.yml + frontend-hpa.yml — scale 2-5 replicas
│       └── backend-pdb.yml + frontend-pdb.yml — minAvailable: 1
├── argocd/
│   └── application.yml      — ArgoCD Application manifest (bootstrap the cluster)
├── terraform/               — IaC (see above)
├── scripts/
│   └── health-check.sh      — checks allexpense.me + all K8s pods + EKS node readiness
├── .github/
│   ├── actions/aws-ecr-login/ — composite action (reused across jobs)
│   └── workflows/deploy.yml — full CI/CD pipeline
└── docker-compose.yml       — local development
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

## Kubernetes

```bash
# Check all running pods
kubectl get pods

# Check pods in monitoring namespace
kubectl get pods -n monitoring

# View backend logs
kubectl logs -l app=backend -f

# Run health check
bash scripts/health-check.sh

# Bootstrap ArgoCD on a fresh cluster
kubectl apply -f argocd/application.yml
```

---

## Security

- Secrets stored in AWS Secrets Manager — never in Git or in K8s manually
- External Secrets Operator syncs secrets to the cluster using IRSA (no static AWS keys)
- Git history scrubbed with `git-filter-repo` after API key incident
- ECR immutable image tags — deployed image is exactly what was tested
- Trivy scans both backend and frontend images, blocks deploys on CRITICAL unfixed CVEs
- `apk upgrade` in frontend Dockerfile patches base image CVEs at every build
- CORS restricted to `https://allexpense.me`
- Branch protection on `main` — PRs required, tests must pass
- EKS control plane audit logging enabled (api, audit, authenticator → CloudWatch, 30-day retention)
- EKS private endpoint access enabled — in-cluster traffic stays within VPC
- nginx security headers on all responses: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
- Liveness and readiness probes on all pods — unhealthy pods are restarted and removed from traffic
- PostgreSQL connection pool (2–20 connections) — prevents connection exhaustion under load
- `/health` endpoint verifies live DB connectivity — Kubernetes probes catch real failures

---

## Monitoring

Prometheus scrapes all cluster components via kube-prometheus-stack. Grafana dashboards show pod health, request rate, memory, and CPU.

Grafana is also exposed publicly at **[grafana.allexpense.me](https://grafana.allexpense.me)**.

```bash
# Port-forward Grafana locally (alternative)
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

# Get Grafana admin password
kubectl get secret -n monitoring monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d
```

---

## Extra Features (beyond academy requirements)

- **Receipt scanner** — photo -> Claude Haiku vision API -> auto-fills expense form
- **Exchange rates** — live USD/EUR from API, historical rate locked at entry time
- **Shared pools** — invite family members, shared expense groups with invite/accept/decline flow
- **Hebrew/English i18n** — full translation throughout the UI
- **Mobile-first** — fully responsive layout, same design on phone and desktop
- **Excel/CSV export** — download expense history
- **Custom month picker** — popup calendar translated in both languages
