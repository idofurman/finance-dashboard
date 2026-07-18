#!/bin/bash

APP_URL="https://allexpense.me"
PASS=0
FAIL=0

ok()   { echo "[OK]   $1"; ((PASS++)); }
fail() { echo "[FAIL] $1"; ((FAIL++)); }

check() {
    local label=$1
    local cmd=$2
    if eval "$cmd" > /dev/null 2>&1; then
        ok "$label"
    else
        fail "$label"
    fi
}

echo ""
echo "========================================="
echo "  Finance Dashboard -- Health Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

echo ""
echo "--- App ---"
check "Frontend reachable (HTTPS)"  "curl -sf $APP_URL/"
check "Backend health (DB check)"   "kubectl exec deployment/backend -- python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:5000/health')\""
check "API responding (auth check)" "curl -sf -o /dev/null -w '%{http_code}' -X POST $APP_URL/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"x\",\"password\":\"y\"}' | grep -q 401"

echo ""
echo "--- Kubernetes Pods ---"
check "Backend pod running"   "kubectl get pods -l app=backend --no-headers | grep -q Running"
check "Frontend pod running"  "kubectl get pods -l app=frontend --no-headers | grep -q Running"
check "Database pod running"  "kubectl get pods -l app=db --no-headers | grep -q Running"
check "Prometheus running"    "kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus --no-headers | grep -q Running"
check "Grafana running"       "kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana --no-headers | grep -q Running"
check "ArgoCD server running" "kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server --no-headers | grep -q Running"

echo ""
echo "--- ArgoCD ---"
check "App synced to GitHub" "kubectl get application finance-dashboard -n argocd -o jsonpath='{.status.sync.status}' | grep -q Synced"

echo ""
echo "--- EKS Nodes ---"
TOTAL_NODES=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
NOT_READY=$(kubectl get nodes --no-headers 2>/dev/null | grep -c NotReady || true)

if [ "$NOT_READY" -eq 0 ] && [ "$TOTAL_NODES" -gt 0 ]; then
    ok "All nodes ready ($TOTAL_NODES nodes)"
else
    fail "Node issue: $NOT_READY/$TOTAL_NODES not ready"
fi

echo ""
echo "========================================="
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL CHECKS PASSED ($PASS/$((PASS+FAIL)))"
else
    echo "  $FAIL CHECK(S) FAILED ($PASS/$((PASS+FAIL)) passed)"
fi
echo "========================================="
echo ""

exit $FAIL
