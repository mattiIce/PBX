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
- `configmap.yaml` - Configuration files (config.yml)
- `secrets.yaml` - Sensitive data (passwords, keys)
- `postgresql.yaml` - PostgreSQL database StatefulSet
- `deployment.yaml` - PBX application deployment
- `service.yaml` - Kubernetes services (LoadBalancer/ClusterIP)
- `ingress.yaml` - Ingress for HTTPS access
- `pvc.yaml` - PersistentVolumeClaims for storage

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Secrets

```bash
kubectl apply -f secrets.yaml
```

### 3. Create ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Deploy PostgreSQL

```bash
kubectl apply -f postgresql.yaml
```

### 5. Deploy PBX Application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 6. Verify Deployment

```bash
kubectl get all -n pbx-system
```

## For full documentation, see the complete Kubernetes deployment guide.
