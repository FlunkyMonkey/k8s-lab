#!/bin/bash
# Full Kubernetes Homelab Health Check

echo "========================================="
echo "KUBERNETES HOMELAB HEALTH CHECK"
echo "========================================="
echo ""

# 1. NODE HEALTH
echo "1. NODE STATUS"
echo "----------------------------------------"
kubectl get nodes -o wide
echo ""

# 2. ALL PODS (looking for anything not Running/Completed)
echo "2. PROBLEMATIC PODS (Not Running/Completed)"
echo "----------------------------------------"
kubectl get pods -A | grep -v "Running\|Completed" | head -20
echo ""

# 3. PODS NOT READY (e.g., 1/2 instead of 2/2)
echo "3. PODS NOT FULLY READY"
echo "----------------------------------------"
kubectl get pods -A | awk '$3 !~ /([0-9]+)\/\1/' | grep -v RESTARTS
echo ""

# 4. ARGOCD APPLICATION STATUS
echo "4. ARGOCD APPLICATIONS"
echo "----------------------------------------"
kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status
echo ""

# 5. CHECK SPECIFICALLY FOR DEGRADED/OUTOFSYNC
echo "5. APPLICATIONS NEEDING ATTENTION"
echo "----------------------------------------"
kubectl get applications -n argocd -o json | jq -r '.items[] | select(.status.sync.status != "Synced" or .status.health.status != "Healthy") | "\(.metadata.name): Sync=\(.status.sync.status) Health=\(.status.health.status)"'
echo ""

# 6. DEPLOYMENTS NOT AVAILABLE
echo "6. DEPLOYMENTS NOT FULLY AVAILABLE"
echo "----------------------------------------"
kubectl get deployments -A | awk '$3 != $4 || $4 != $5'
echo ""

# 7. STATEFULSETS NOT READY
echo "7. STATEFULSETS STATUS"
echo "----------------------------------------"
kubectl get statefulsets -A
echo ""

# 8. DAEMONSETS STATUS
echo "8. DAEMONSETS STATUS"
echo "----------------------------------------"
kubectl get daemonsets -A
echo ""

# 9. PERSISTENT VOLUME CLAIMS
echo "9. PVCS NOT BOUND"
echo "----------------------------------------"
kubectl get pvc -A | grep -v Bound
echo ""

# 10. EVENTS (WARNINGS IN LAST HOUR)
echo "10. WARNING EVENTS (Last Hour)"
echo "----------------------------------------"
kubectl get events -A --field-selector type=Warning --sort-by='.lastTimestamp' | tail -20
echo ""

# 11. CEPH HEALTH
echo "11. CEPH CLUSTER HEALTH"
echo "----------------------------------------"
kubectl -n rook-ceph exec -it deploy/rook-ceph-tools -- ceph status 2>/dev/null || echo "Ceph tools not available"
echo ""

# 12. SERVICE CONNECTIVITY
echo "12. SERVICE LOADBALANCER IPS"
echo "----------------------------------------"
kubectl get svc -A -o wide | grep LoadBalancer
echo ""

echo "========================================="
echo "HEALTH CHECK COMPLETE"
echo "========================================="
