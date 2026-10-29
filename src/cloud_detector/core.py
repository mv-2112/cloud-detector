import urllib.request
import urllib.error
import socket
import os
from typing import Dict, List, Tuple

def check_infra() -> Tuple[str, List[str]]:
    METADATA_IP = "169.254.169.254"
    TIMEOUT = 1.0
    
    infra = "Unknown"
    not_infra = []

    # 1. AWS Test
    is_aws = False
    try:
        token_req = urllib.request.Request(
            f"http://{METADATA_IP}/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
            method="PUT"
        )
        try:
            with urllib.request.urlopen(token_req, timeout=TIMEOUT) as token_resp:
                if token_resp.status == 200:
                    is_aws = True
        except (urllib.error.URLError, socket.timeout):
            with urllib.request.urlopen(f"http://{METADATA_IP}/latest/meta-data/instance-id", timeout=TIMEOUT) as response:
                if response.status == 200:
                    is_aws = True
    except (urllib.error.URLError, socket.timeout):
        pass

    if is_aws:
        infra = "AWS"
        not_infra.extend(["Azure", "GCP", "OpenStack", "VCF"])
    else:
        not_infra.append("AWS")

        # 2. Azure Test
        if infra == "Unknown":
            try:
                req = urllib.request.Request(
                    f"http://{METADATA_IP}/metadata/instance?api-version=2021-02-01",
                    headers={"Metadata": "true"}
                )
                with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                    if response.status == 200:
                        infra = "Azure"
                        not_infra.extend(["GCP", "OpenStack", "VCF"])
            except (urllib.error.URLError, socket.timeout):
                not_infra.append("Azure")

        # 3. GCP Test
        if infra == "Unknown":
            try:
                req = urllib.request.Request(
                    f"http://{METADATA_IP}/computeMetadata/v1/instance/id",
                    headers={"Metadata-Flavor": "google"}
                )
                with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                    if response.status == 200:
                        infra = "GCP"
                        not_infra.extend(["OpenStack", "VCF"])
            except (urllib.error.URLError, socket.timeout):
                not_infra.append("GCP")

        # 4. OpenStack Test
        if infra == "Unknown":
            try:
                with urllib.request.urlopen(f"http://{METADATA_IP}/openstack", timeout=TIMEOUT) as response:
                    if response.status == 200:
                        infra = "OpenStack"
                        not_infra.append("VCF")
            except (urllib.error.URLError, socket.timeout):
                not_infra.append("OpenStack")

        # 5. VCF Block Storage Check Fallback
        if infra == "Unknown" and os.path.exists("/sys/block"):
            try:
                for dev in os.listdir("/sys/block"):
                    vendor_path = f"/sys/block/{dev}/device/vendor"
                    if os.path.exists(vendor_path):
                        with open(vendor_path, "r") as f:
                            if "vmware" in f.read().lower():
                                infra = "VCF"
                                break
            except Exception:
                pass
        
        if infra != "VCF":
            not_infra.append("VCF")

    return infra, sorted(list(set(not_infra)))

def scan_proc_mounts_for_flavor() -> str:
    """Scans unprivileged mount tables to identify local cluster paths."""
    try:
        if os.path.exists("/proc/self/mountinfo"):
            with open("/proc/self/mountinfo", "r") as f:
                content = f.read().lower()
                # MicroK8s runs inside snap directories on the host
                if "microk8s" in content or "/snap/microk8s" in content:
                    return "MicroK8s"
                # K3s uses explicit runtime /var/lib/rancher data tracks
                if "k3s" in content or "rancher" in content:
                    return "K3s"
    except Exception:
        pass
    return "Standard"

def check_runtime() -> Tuple[str, List[str]]:
    runtime = "Unknown"
    not_runtime = []

    has_k8s_token = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
    has_openshift_env = any("OPENSHIFT" in key for key in os.environ)
    
    env_keys = "".join(os.environ.keys()).upper()
    env_vals = "".join(os.environ.values()).upper()

    if has_k8s_token:
        not_runtime.extend(["Docker", "Magnum"])
        k8s_port = os.environ.get("KUBERNETES_SERVICE_PORT", "")
        
        # 1. Managed Platforms / Enterprise Cloud Tracks
        if has_openshift_env or "OPENSHIFT" in env_vals:
            runtime = "OCP (OpenShift)"
            not_runtime.extend(["AKS", "EKS", "GKE", "Vanilla K8s"])
        elif "AKS_" in env_keys or "AZURE" in env_keys:
            runtime = "AKS"
            not_runtime.extend(["OCP (OpenShift)", "EKS", "GKE", "Vanilla K8s"])
        elif "EKS_" in env_keys or "AWS_ROLE" in env_keys:
            runtime = "EKS"
            not_runtime.extend(["OCP (OpenShift)", "AKS", "GKE", "Vanilla K8s"])
        elif "GKE_" in env_keys or "GOOGLE_" in env_keys:
            runtime = "GKE"
            not_runtime.extend(["OCP (OpenShift)", "AKS", "EKS", "Vanilla K8s"])
            
        # 2. Local / Custom Distributions
        else:
            flavour = "Standard"
            
            if k8s_port == "16443" or "MICROK8S" in env_vals or "MICROK8S" in env_keys:
                flavour = "MicroK8s"
            elif "MINIKUBE" in env_keys:
                flavour = "Minikube"
            elif "K3S" in env_keys or "K3S_NODE" in env_keys:
                flavour = "K3s"
            else:
                # Direct environment variables missing -> Fall back to deep mount checking
                flavour = scan_proc_mounts_for_flavor()
                
            runtime = f"Vanilla K8s ({flavour})"
            not_runtime.extend(["OCP (OpenShift)", "AKS", "EKS", "GKE"])
    else:
        not_runtime.extend(["OCP (OpenShift)", "AKS", "EKS", "GKE", "Vanilla K8s"])
        
        if "MAGNUM" in env_keys or "COE_" in env_keys:
            runtime = "Magnum"
            not_runtime.append("Docker")
        else:
            not_runtime.append("Magnum")
            if os.path.exists("/.dockerenv") or any("DOCKER" in key for key in os.environ):
                runtime = "Docker"
            else:
                not_runtime.append("Docker")

    return runtime, sorted(list(set(not_runtime)))

def detect_all() -> Dict:
    infra, not_infra = check_infra()
    runtime, not_runtime = check_runtime()
    
    return {
        "infrastructure": infra,
        "runtime": runtime,
        "exclusions": {
            "infrastructure": not_infra,
            "runtime": not_runtime
        }
    }
