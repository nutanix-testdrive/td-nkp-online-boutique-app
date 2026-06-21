# NKP Entrypoint Integration Guide

This document explains how to integrate the AppDeployment-based deployment with the td-entrypoint automation.

## Overview

The td-entrypoint repository has an NKP manager (`tdtypes/nkp/manager/nkp_manager.py`) that orchestrates the Test Drive setup. Currently, it uses the `nkp create catalog-application` CLI command to deploy the Online Boutique app. This integration provides an alternative GitOps-based approach where AppDeployment manifests are applied directly from Git.

## Current Flow (td-entrypoint)

```
nkp_entrypoint.py:
1. create_nkp_images()
2. create_bastion_vm()
3. wait_for_ssh_ready()
4. create_nkp_cluster()
5. setup_kubeconfig_env()
6. apply_nkp_license()
7. create_managed_workload_cluster()
8. create_workspace()
9. create_project()
10. attach_workload_cluster_to_workspace()
11. deploy_online_boutique()  ← Uses NKP CLI
12. configure_kommander_ingress()
13. get_nkp_dashboard_info()
14. post_component_update()
```

## Integration Options

### Option 1: Replace Existing Method (Recommended)

Replace the current `deploy_online_boutique()` implementation in `nkp_manager.py` with the method from `deploy_via_appdeployment.py`.

**Advantages:**
- True GitOps: Manifests are version controlled in Git
- No dependency on NKP CLI for application deployment
- More transparent: You can see exactly what resources are being created
- Easier to customize and extend

**Changes Required:**
1. Copy the method from `deploy_via_appdeployment.py` to `nkp_manager.py`
2. Replace or update the existing `deploy_online_boutique()` method
3. No changes to `nkp_entrypoint.py` needed (method signature is compatible)

### Option 2: Add as Alternative Method

Keep both methods and allow selection via config.

**Implementation:**
```python
# In nkp_manager.py
def deploy_online_boutique(self, bastion_vm_ip, workspace_name="my-edge-application", project_name="online-boutique"):
    deployment_method = self.config.get("online_boutique_deployment_method", "cli")
    
    if deployment_method == "appdeployment":
        return self.deploy_online_boutique_via_appdeployment(
            bastion_vm_ip, workspace_name, project_name
        )
    else:
        # Keep existing CLI implementation
        return self._deploy_online_boutique_via_cli(
            bastion_vm_ip, workspace_name, project_name
        )
```

## Key Differences from CLI Method

| Aspect | NKP CLI Method | AppDeployment from Git |
|--------|----------------|------------------------|
| **Resources created in** | `kommander` namespace | `kommander` namespace |
| **Command** | `nkp create catalog-application` | `kubectl apply -k <git-url>` |
| **Source of truth** | CLI flags | Git repository manifests |
| **Versioning** | Branch/ref specified in CLI | Branch/ref in git URL |
| **Customization** | CLI flags only | Edit manifests in Git |
| **Transparency** | Black box (CLI creates resources) | Clear (manifests visible in Git) |

## Configuration Alignment

The AppDeployment manifests are configured to match the existing entrypoint behavior:

```yaml
# Workspace (from nkp_workspace.json)
name: my-edge-application
namespace: my-edge-application

# Project (from nkp_project.json)
name: online-boutique
namespace: online-boutique
workspace: my-edge-application

# AppDeployment
namespace: kommander  # Resources created in kommander namespace
clusterSelector:
  matchLabels:
    workspace: my-edge-application  # Targets workload clusters with this label
```

## Cluster Labeling

The `deploy_via_appdeployment.py` method automatically labels the workload cluster to match the AppDeployment selector:

```bash
kubectl label cluster <workload-cluster-name> -n kommander workspace=my-edge-application
```

This ensures the app deploys to the correct cluster.

## Verification

After deployment, the same verification commands work:

```bash
# Check AppDeployment resources
kubectl get gitrepository,app,appdeployment -n kommander | grep online-boutique

# Check if app is deploying to workload clusters
kubectl get appdeploymentinstance -n kommander

# On the workload cluster
kubectl get pods -n online-boutique
kubectl get svc frontend-external -n online-boutique
```

## Configuration Schema (No Changes Required)

The existing config structure from the entrypoint works as-is:

```json
{
  "workspace_config": {
    "name": "my-edge-application",
    "display_name": "my edge application"
  },
  "project_config": {
    "name": "online-boutique",
    "workspace_name": "my-edge-application",
    "namespace_labels": {},
    "quotas": {
      "cpu": "10",
      "memory": "20Gi"
    }
  }
}
```

No additional configuration is needed to use the AppDeployment method.

## Testing

To test the integration:

1. Run the entrypoint with the updated `deploy_online_boutique()` method
2. Verify the resources are created:
   ```bash
   kubectl get gitrepository,app,appdeployment -n kommander
   ```
3. Check that the app deploys to the workload cluster:
   ```bash
   kubectl get pods -n online-boutique
   ```
4. Verify the frontend service gets a LoadBalancer IP:
   ```bash
   kubectl get svc frontend-external -n online-boutique
   ```

## Rollback

If issues occur, you can easily rollback by:

1. Keeping the original CLI-based method as a backup
2. Or manually deleting the AppDeployment resources:
   ```bash
   kubectl delete -k https://github.com/nutanix-testdrive/td-nkp-online-boutique-app/deployment?ref=ft/nkp
   ```
3. Then re-running with the CLI method

## Benefits for Test Drive

Using AppDeployment from Git provides these advantages for the Test Drive:

1. **Transparency**: Users can inspect the exact manifests being applied
2. **Customization**: Easy to fork and customize for different demo scenarios
3. **GitOps Best Practice**: Demonstrates true GitOps workflow
4. **Version Control**: All changes tracked in Git
5. **Reproducibility**: Same manifests produce same results
6. **No CLI Dependency**: Works with standard kubectl commands

## Next Steps

1. Copy `deploy_via_appdeployment.py` method to `nkp_manager.py`
2. Update or replace the existing `deploy_online_boutique()` method
3. Test the deployment flow end-to-end
4. Commit and push the changes to the ft/nkp branch
5. Update any documentation to reflect the new GitOps approach
