# Quick Start: AppDeployment Auto-Deployment

## TL;DR

Apply these manifests from Git to automatically deploy Online Boutique to your NKP workload cluster:

```bash
kubectl apply -k https://github.com/nutanix-testdrive/td-nkp-online-boutique-app/deployment?ref=ft/nkp
```

Then label your workload cluster:

```bash
kubectl label cluster <your-workload-cluster-name> -n kommander workspace=my-edge-application
```

That's it! The app will automatically deploy to your cluster.

---

## What This Does

1. **Creates GitRepository**: Points to this GitHub repo (ft/nkp branch)
2. **Creates App**: Defines the Helm chart location (./helm-chart)
3. **Creates ConfigMap**: Sets configuration values (image, Redis, etc.)
4. **Creates AppDeployment**: Manages deployment to clusters with matching labels

## Where Resources Are Created

All resources are created in the `kommander` namespace on the **management cluster**:

```
Management Cluster (kommander namespace):
├── GitRepository: online-boutique-catalog
├── App: online-boutique
├── ConfigMap: online-boutique-overrides
└── AppDeployment: online-boutique
    └── (Triggers deployment to workload clusters)

Workload Cluster (online-boutique namespace):
├── HelmRelease: online-boutique
├── All app pods (frontend, cart, payment, etc.)
└── Service: frontend-external (LoadBalancer)
```

## How It Works with NKP

```
┌─────────────────────────────────────────────────────┐
│ GitHub Repo (ft/nkp branch)                         │
│ └── deployment/                                     │
│     ├── gitrepository.yaml                          │
│     ├── app.yaml                                    │
│     ├── configmap.yaml                              │
│     └── appdeployment.yaml                          │
└─────────────────────────────────────────────────────┘
                    │
                    │ kubectl apply -k
                    ▼
┌─────────────────────────────────────────────────────┐
│ Management Cluster (kommander namespace)            │
│                                                     │
│ ┌────────────────┐         ┌──────────────┐       │
│ │ GitRepository  │────────▶│ FluxCD       │       │
│ └────────────────┘         └──────────────┘       │
│                                   │                │
│ ┌────────────────┐                │                │
│ │ App            │◀───────────────┘                │
│ └────────────────┘                                 │
│                                                     │
│ ┌────────────────┐                                 │
│ │ ConfigMap      │                                 │
│ └────────────────┘                                 │
│                                                     │
│ ┌────────────────────────────────────────┐         │
│ │ AppDeployment                          │         │
│ │   clusterSelector:                     │         │
│ │     matchLabels:                       │         │
│ │       workspace: my-edge-application   │         │
│ └────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────┘
                    │
                    │ Kommander Controller
                    │ creates AppDeploymentInstance
                    ▼
┌─────────────────────────────────────────────────────┐
│ Workload Cluster (online-boutique namespace)        │
│                                                     │
│ ┌────────────────┐         ┌──────────────┐       │
│ │ HelmRelease    │────────▶│ Helm         │       │
│ └────────────────┘         └──────────────┘       │
│                                   │                │
│                                   ▼                │
│ ┌──────────────────────────────────────────┐      │
│ │ Online Boutique Pods                     │      │
│ │ - frontend                               │      │
│ │ - cartservice                            │      │
│ │ - productcatalogservice                  │      │
│ │ - paymentservice                         │      │
│ │ - ... (11 microservices total)           │      │
│ └──────────────────────────────────────────┘      │
│                                                     │
│ ┌──────────────────────────────────────────┐      │
│ │ Service: frontend-external (LoadBalancer)│      │
│ │ Type: LoadBalancer                        │      │
│ │ IP: <assigned-by-metallb>                 │      │
│ └──────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

## Cluster Selection

The AppDeployment looks for clusters with this label:

```yaml
workspace: my-edge-application
```

**To label your cluster:**

```bash
# Find your cluster name
kubectl get clusters -n kommander

# Label it
kubectl label cluster <cluster-name> -n kommander workspace=my-edge-application
```

## Verify Deployment

### On Management Cluster

```bash
# Check resources
kubectl get gitrepository,app,appdeployment -n kommander | grep online-boutique

# Check GitRepository status
kubectl get gitrepository online-boutique-catalog -n kommander -o yaml

# Check AppDeployment status
kubectl describe appdeployment online-boutique -n kommander

# Check which clusters it's deploying to
kubectl get appdeploymentinstance -n kommander
```

### On Workload Cluster

```bash
# Switch context to workload cluster
kubectl config use-context <workload-cluster-context>

# Check pods
kubectl get pods -n online-boutique

# Check services
kubectl get svc -n online-boutique

# Get LoadBalancer IP
kubectl get svc frontend-external -n online-boutique
```

## Customize Configuration

Edit `deployment/configmap.yaml` in this repo to customize:

```yaml
data:
  values.yaml: |
    images:
      repository: us-central1-docker.pkg.dev/google-samples/microservices-demo
      tag: v0.10.5  # Change version here
    frontend:
      externalService: true  # Set to false for ClusterIP
    cartDatabase:
      type: redis
      inClusterRedis:
        create: true  # Set to false to use external Redis
```

Then commit and push. FluxCD will automatically reconcile the changes.

## Troubleshooting

### GitRepository not ready

```bash
kubectl describe gitrepository online-boutique-catalog -n kommander
```

Check the status conditions and events. Common issues:
- Git URL not accessible
- Branch doesn't exist
- Authentication required (shouldn't be for public repos)

### AppDeployment not creating instances

```bash
kubectl describe appdeployment online-boutique -n kommander
```

Check:
- Are any clusters labeled with `workspace: my-edge-application`?
- Is the cluster attached to the workspace?

### App not deploying to workload cluster

```bash
# Check AppDeploymentInstance
kubectl get appdeploymentinstance -n kommander -o yaml

# Check FluxCD on workload cluster
kubectl get kustomization -A
kubectl get helmrelease -A
```

## Clean Up

To remove the AppDeployment:

```bash
kubectl delete -k https://github.com/nutanix-testdrive/td-nkp-online-boutique-app/deployment?ref=ft/nkp
```

This will remove the AppDeployment and related resources, which will trigger cleanup on workload clusters.

## For td-entrypoint Integration

See `ENTRYPOINT_INTEGRATION.md` for details on integrating this with the td-entrypoint automation.
