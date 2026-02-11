# Homelab MCP Server

Model Context Protocol server exposing vGriz homelab infrastructure tools.

## Available Tools

- `get_k8s_nodes` - Kubernetes node status
- `get_k8s_pods` - Pod status across namespaces
- `get_argocd_apps` - ArgoCD application health
- `get_ceph_status` - Rook-Ceph cluster status
- `get_prometheus_alerts` - Active Prometheus alerts

## Deployment

Deployed via ArgoCD GitOps to Kubernetes cluster.

## Access

Service exposed via MetalLB LoadBalancer (will be assigned 172.18.1.x IP)
