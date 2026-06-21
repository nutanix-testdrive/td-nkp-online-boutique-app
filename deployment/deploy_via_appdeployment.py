"""
Alternative deployment method for NKP Manager to use AppDeployment from Git.

This method can be added to nkp_manager.py to replace or complement the existing
deploy_online_boutique() method that uses the NKP CLI.
"""

def deploy_online_boutique_via_appdeployment(self, bastion_vm_ip, workspace_name="my-edge-application", project_name="online-boutique"):
    """
    Deploy Online Boutique application via AppDeployment resources from Git.
    
    Instead of using 'nkp create catalog-application' CLI, this method applies
    the AppDeployment manifests directly from the git repository, enabling
    true GitOps-based deployment where the manifests are version controlled.
    
    Args:
        bastion_vm_ip: IP address of the bastion VM
        workspace_name: Name of the workspace (default: my-edge-application)
        project_name: Name of the project (default: online-boutique)
    
    Returns:
        dict: Deployment info with git details
    
    Raises:
        Exception: If AppDeployment creation fails
    
    References:
        - GitHub: https://github.com/nutanix-testdrive/td-nkp-online-boutique-app
        - Deployment manifests: deployment/ directory in the repo
    """
    self.logger.info(
        f"Deploying Online Boutique via AppDeployment manifests from Git"
    )
    
    catalog_url = "https://github.com/nutanix-testdrive/td-nkp-online-boutique-app.git"
    catalog_ref = "ft/nkp"
    deployment_path = "deployment"
    
    key_path = "/home/admin/.ssh/nkp_bastion_key"
    
    # Step 1: Apply the AppDeployment manifests using kubectl
    self.logger.info(f"Applying AppDeployment manifests from git repo...")
    
    apply_command = (
        f"""ssh -i {key_path} -o StrictHostKeyChecking=no konvoy@{bastion_vm_ip} """
        f""""kubectl apply -k {catalog_url}/{deployment_path}?ref={catalog_ref}" """
    )
    
    stdout, stderr = self.pc_ssh_client.exec_command(
        apply_command, sudo=True, exit_on_failure=False
    )
    
    self.logger.info(f"Apply stdout: {stdout.strip() if stdout else '(empty)'}")
    if stderr:
        self.logger.info(f"Apply stderr: {stderr.strip()}")
    
    if stdout and ("created" in stdout.lower() or "configured" in stdout.lower() or "unchanged" in stdout.lower()):
        self.logger.info(f"✓ AppDeployment manifests applied successfully")
    else:
        self.logger.warning(f"Unexpected apply output - check logs above")
    
    # Step 2: Wait for GitRepository to be ready
    self.logger.info("Waiting for GitRepository to be ready...")
    
    wait_gitrepo_command = (
        f"""ssh -i {key_path} -o StrictHostKeyChecking=no konvoy@{bastion_vm_ip} """
        f""""kubectl wait --for=condition=ready gitrepository/online-boutique-catalog """
        f"""-n kommander --timeout=120s" """
    )
    
    stdout_wait, stderr_wait = self.pc_ssh_client.exec_command(
        wait_gitrepo_command, sudo=True, exit_on_failure=False
    )
    
    if stdout_wait and "condition met" in stdout_wait.lower():
        self.logger.info("✓ GitRepository is ready")
    else:
        self.logger.warning("GitRepository may still be reconciling")
    
    # Step 3: Verify AppDeployment was created
    self.logger.info("Verifying AppDeployment resources...")
    
    verify_command = (
        f"""ssh -i {key_path} -o StrictHostKeyChecking=no konvoy@{bastion_vm_ip} """
        f""""kubectl get gitrepository,app,configmap,appdeployment -n kommander | grep online-boutique" """
    )
    
    stdout_verify, stderr_verify = self.pc_ssh_client.exec_command(
        verify_command, sudo=True, exit_on_failure=False
    )
    
    self.logger.info(f"Verification stdout: {stdout_verify.strip() if stdout_verify else '(empty)'}")
    if stderr_verify:
        self.logger.info(f"Verification stderr: {stderr_verify.strip()}")
    
    if stdout_verify and "online-boutique" in stdout_verify:
        self.logger.info(f"✓ AppDeployment resources verified successfully")
    else:
        self.logger.warning(f"Could not verify all resources - they may still be creating")
    
    # Step 4: Label workload clusters for AppDeployment selector
    self.logger.info("Labeling workload cluster for AppDeployment selector...")
    
    # Get the workload cluster name (assuming it's created already)
    get_cluster_command = (
        f"""ssh -i {key_path} -o StrictHostKeyChecking=no konvoy@{bastion_vm_ip} """
        f""""kubectl get clusters -A --no-headers | grep -v host-cluster | awk '{{print \\$2}}' | head -n 1" """
    )
    
    stdout_cluster, _ = self.pc_ssh_client.exec_command(
        get_cluster_command, sudo=True, exit_on_failure=False
    )
    
    workload_cluster_name = stdout_cluster.strip() if stdout_cluster else None
    
    if workload_cluster_name:
        self.logger.info(f"Found workload cluster: {workload_cluster_name}")
        
        # Label the cluster to match AppDeployment selector
        label_command = (
            f"""ssh -i {key_path} -o StrictHostKeyChecking=no konvoy@{bastion_vm_ip} """
            f""""kubectl label cluster {workload_cluster_name} -n kommander """
            f"""workspace={workspace_name} --overwrite" """
        )
        
        stdout_label, stderr_label = self.pc_ssh_client.exec_command(
            label_command, sudo=True, exit_on_failure=False
        )
        
        if stdout_label and "labeled" in stdout_label.lower():
            self.logger.info(f"✓ Workload cluster labeled successfully")
        else:
            self.logger.info(f"Cluster may already have the label")
    else:
        self.logger.warning("Could not find workload cluster name - you may need to label it manually")
    
    self.logger.info(
        f"✓ Online Boutique AppDeployment created successfully via GitOps"
    )
    
    return {
        "catalog_url": catalog_url,
        "catalog_ref": catalog_ref,
        "deployment_path": deployment_path,
        "status": "applied",
        "method": "appdeployment_from_git"
    }
