# Kubernetes Deployment for Warden VoIP PBX

This directory contains Kubernetes manifests for deploying the PBX system in a production environment.

## Overview

The PBX system can be deployed on Kubernetes for:
- **High Availability**: Multiple replicas with automatic failover
- **Scalability**: Horizontal scaling based on load
- **Resource Management**: CPU/memory limits and requests
- **Health Monitoring**: Liveness and readiness probes
- **Service Discovery**: Kubernetes service for load balancing

## Files

- `namespace.yaml` - Namespace for PBX resources
- `deployment.yaml` - PBX application deployment with ConfigMap and Secret templates
- `service.yaml` - Kubernetes services (LoadBalancer for PBX, ClusterIP for PostgreSQL)
- `pvc.yaml` - PersistentVolumeClaims for storage

**Note:** ConfigMap and Secret templates are included in `deployment.yaml`. You may want to extract them into separate files for easier management. PostgreSQL StatefulSet is not included - see service.yaml for deployment options.

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Persistent Volume Claims

```bash
kubectl apply -f pvc.yaml
```

Note: Ensure your cluster has a storage class that supports ReadWriteMany for shared volumes, or modify pvc.yaml to use ReadWriteOnce.

### 3. Deploy PostgreSQL (Required)

The `service.yaml` includes a PostgreSQL service definition, but you need to deploy PostgreSQL separately. Options:

**Option A: Use Helm**
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install pbx-postgresql bitnami/postgresql \
  --namespace pbx-system \
  --set auth.username=pbx_user \
  --set auth.password=changeme \
  --set auth.database=pbx_system
```

**Option B: Create your own StatefulSet** (not provided in these manifests)

**Option C: Use external managed database** (modify deployment.yaml environment variables)

### 4. Review and Customize Configuration

Edit `deployment.yaml` to customize:
- ConfigMap `pbx-config`: Update with your actual config.yml content
- Secret `pbx-ssl-cert`: Add your SSL certificate and private key
- Secret `pbx-secrets`: Set your database credentials

### 5. Deploy PBX Application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 6. Verify Deployment

```bash
kubectl get all -n pbx-system
kubectl get pvc -n pbx-system
kubectl logs -n pbx-system -l app=pbx-server
```

## For full documentation, see the complete Kubernetes deployment guide.
