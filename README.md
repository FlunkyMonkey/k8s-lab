# Kubernetes Homelab Backup

Configuration files for kube.vgriz.com cluster.

## Cluster Info
- 3 nodes: kube1, kube2, kube3 (172.18.1.61-63)
- VIP: 172.18.1.60
- Kubernetes: v1.31.13

## Files

### Monitoring
- `prometheus-values.yaml` - Prometheus/Grafana stack
- `loki-values.yaml` - Loki logging

### Storage  
- `rook-ceph-values.yaml` - Ceph operator
- `ceph-cluster.yaml` - Ceph cluster config
- `nfs-values.yaml` - NFS provisioner

### Network
- `metallb-ippool.yaml` - LoadBalancer IP pool (172.18.1.200-249)
- `metallb-l2.yaml` - Layer 2 advertisement

## Rebuild Commands

See docs/ folder for detailed procedures.
