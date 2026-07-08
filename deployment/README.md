# NKP AppDeployment for Online Boutique

This directory contains the NKP AppDeployment resources for automatically deploying the Online Boutique application to workload clusters via GitOps.

## Integration with td-entrypoint

This deployment configuration is designed to work with the NKP entrypoint automation. It provides an alternative to using the `nkp create catalog-application` CLI command by applying manifests directly from Git.

## Resources

1. **gitrepository.yaml**: FluxCD GitRepository resource that points to this repo
2. **app.yaml**: NKP App resource that defines the application and its Helm chart
3. **configmap.yaml**: Configuration overrides for the Helm chart (values.yaml)
4. **appdeployment.yaml**: AppDeployment resource that manages deployment to selected clusters
5. **kustomization.yaml**: Kustomize manifest to apply all resources together

## Deployment Flow

1. These manifests are applied to the NKP Management cluster in the `my-edge-application` workspace namespace
2. The AppDeployment controller detects the new AppDeployment resource
3. Based on the `clusterSelector`, it identifies target workload clusters
4. For each matching cluster, it creates an AppDeploymentInstance and generates a Kustomization
5. FluxCD on the workload cluster pulls the Kustomization and deploys the HelmRelease
6. The Online Boutique app is deployed to the `online-boutique` namespace on the workload cluster

## Prerequisites

- NKP Management cluster with Kommander installed
- Workspace named `my-edge-application` must exist
- Workload cluster(s) must be attached to the workspace and have matching labels

## Applying the AppDeployment

### Option 1: Direct kubectl apply
```bash
kubectl apply -k deployment/
```

### Option 2: GitOps via kubectl (Recommended for td-entrypoint)
Apply directly from the git repository:

```bash
kubectl apply -k https://github.com/nutanix-testdrive/td-nkp-online-boutique-app/deployment?ref=ft/nkp
```

This is the method used in the `deploy_via_appdeployment.py` implementation for the NKP manager.

### Option 3: Using the NKP Manager method
See `deploy_via_appdeployment.py` for a Python method that can be added to `nkp_manager.py` in the td-entrypoint repo. This method:
1. Applies the manifests from Git using kubectl
2. Waits for GitRepository to be ready
3. Verifies all resources were created
4. Labels the workload cluster to match the AppDeployment selector

### Option 4: FluxCD Kustomization (Advanced GitOps)
Create a FluxCD Kustomization on the management cluster that watches this directory:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: online-boutique-appdeployment
  namespace: kommander
spec:
  interval: 5m
  path: ./deployment
  prune: true
  sourceRef:
    kind: GitRepository
    name: online-boutique-catalog
  targetNamespace: kommander
```

## Customization

### Targeting Specific Clusters

The AppDeployment currently uses this selector:

```yaml
spec:
  clusterSelector:
    matchLabels:
      workspace: my-edge-application
```

Your workload cluster must have this label for the app to deploy. To label your cluster:

```bash
kubectl label cluster <cluster-name> -n kommander workspace=my-edge-application
```

Alternatively, edit the `clusterSelector` in `appdeployment.yaml` to match different labels:

```yaml
spec:
  clusterSelector:
    matchLabels:
      infraid: "pc-identifier"  # Match clusters with this label
      environment: production    # Add additional label criteria
```

### Changing Configuration

Edit the `values.yaml` content in `configmap.yaml` to customize:
- Image repository and tag
- Frontend service type
- Redis configuration
- Resource limits
- Any other Helm chart values

### Version Upgrades

To upgrade the application version:
1. Update the `tag` in `configmap.yaml`
2. Optionally update the `version` in `app.yaml`
3. Commit and push changes
4. FluxCD will automatically reconcile the changes

## Verification

Check AppDeployment status:
```bash
kubectl get appdeployment -n my-edge-application
kubectl describe appdeployment online-boutique -n my-edge-application
```

Check AppDeploymentInstance for each cluster:
```bash
kubectl get appdeploymentinstance -n my-edge-application
```

Check the app on the workload cluster:
```bash
# Switch to workload cluster context
kubectl get pods -n online-boutique
kubectl get svc frontend-external -n online-boutique
```

## Troubleshooting

- **AppDeployment not creating instances**: Check cluster labels match the selector
- **App not deploying to cluster**: Check FluxCD Kustomization status on the workload cluster
- **HelmRelease fails**: Check the ConfigMap values and Helm chart compatibility
