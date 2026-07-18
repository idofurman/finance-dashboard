#!/bin/bash
# Health check script for the Finance Dashboard infrastructure

APP_URL="https://allexpense.me"
PASS=0
FAIL=0

green() { echo -e "\033[32m✅ $1\033[0m"; }
red()   { echo -e "\033[31m❌ $1\033[0m"; }

check() {
    local label=$1
    local cmd=$2
    if eval "$cmd" > /dev/null 2>&1; then
        green "$label"
        ((PASS++))
    else
        red "$label"
        ((FAIL++))
    fi
}

echo ""
echo "========================================="
echo "  Finance Dashboard — Health Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

echo ""
echo "--- App ---"
check "Flask app responding" "curl -sf $APP_URL/health"

echo ""
echo "--- Kubernetes Pods ---"
check "Backend pod running" "kubectl get pods -l app=backend --no-headers | grep -q Running"
check "Database pod running" "kubectl get pods -l app=db --no-headers | grep -q Running"
check "Prometheus running"  "kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus --no-headers | grep -q Running"
check "Grafana running"     "kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana --no-headers | grep -q Running"
check "ArgoCD server running" "kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server --no-headers | grep -q Running"

echo ""
echo "--- ArgoCD ---"
check "App synced to GitHub" "kubectl get application finance-dashboard -n argocd -o jsonpath='{.status.sync.status}' | grep -q Synced"

echo ""
echo "--- System Resources ---"
DISK=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
MEM_AVAIL=$(free -m | awk '/^Mem:/ {print $7}')

if [ "$DISK" -lt 80 ]; then
    green "Disk usage: ${DISK}%"
    ((PASS++))
else
    red "Disk usage: ${DISK}% (critical — above 80%)"
    ((FAIL++))
fi

if [ "$MEM_AVAIL" -gt 200 ]; then
    green "Available memory: ${MEM_AVAIL}MB"
    ((PASS++))
else
    red "Available memory: ${MEM_AVAIL}MB (low — under 200MB)"
    ((FAIL++))
fi

echo ""
echo "========================================="
if [ "$FAIL" -eq 0 ]; then
    echo -e "\033[32m  ALL CHECKS PASSED ($PASS/$((PASS+FAIL)))\033[0m"
else
    echo -e "\033[31m  $FAIL CHECK(S) FAILED ($PASS/$((PASS+FAIL)) passed)\033[0m"
fi
echo "========================================="
echo ""

exit $FAIL
