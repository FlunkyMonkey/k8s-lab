# Backup Strategy - IMPLEMENTED

Enterprise-grade backup using Velero + MinIO.

## Architecture

- **Velero:** Kubernetes backup/restore tool
- **MinIO:** S3-compatible object storage at 172.18.1.205
- **Storage Backend:** NFS (TrueNAS 172.18.1.97) - 100GB allocated

## Backup Schedules

| Schedule | Runs | Retention | Includes |
|----------|------|-----------|----------|
| daily-backup | 2:00 AM daily | 7 days | monitoring, argocd, rook-ceph |
| weekly-full | 3:00 AM Sunday | 30 days | Entire cluster |

## Access

**MinIO Console:** http://172.18.1.205:9001
- Username: minio
- Password: minio123

## Common Commands

### Check backups
```bash
velero backup get
velero schedule get
```

### Manual backup
```bash
velero backup create manual-backup --wait
```

### Restore entire namespace
```bash
velero restore create --from-backup <backup-name> --wait
```

### Restore specific resources
```bash
velero restore create --from-backup <backup-name> \
  --include-resources deployments,configmaps \
  --namespace-mappings old-ns:new-ns
```

## Disaster Recovery

If cluster is completely lost:

1. Build new cluster (see DEPLOYMENT.md)
2. Install Velero pointing to same MinIO:
```bash
   velero install --provider aws \
     --plugins velero/velero-plugin-for-aws:v1.10.0 \
     --bucket velero \
     --secret-file ./velero-credentials \
     --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://172.18.1.205:9000
```
3. Restore from backup:
```bash
   velero restore create --from-backup weekly-full-<date>
```

## Storage Usage

Check MinIO usage:
```bash
mc du myminio/velero
```

Current allocation: 100GB on NFS

## Tested

✅ Backup creation - Working  
✅ Restore to same cluster - Working  
✅ Namespace deletion/restoration - Working  
✅ ConfigMaps and Secrets - Working

Recovery Time Objective (RTO): ~15 minutes  
Recovery Point Objective (RPO): 24 hours (daily backups)
