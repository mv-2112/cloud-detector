# Cloud Detector

A container-safe, unprivileged cloud infrastructure and container runtime detection engine. It targets link-local Instance Metadata Services (IMDS) at `169.254.169.254`, container runtime namespaces, and fallback filesystem hooks to dynamically map and audit cluster distributions.

---

## 1. Tutorials (Learning-Oriented)

This tutorial walks you through setting up Cloud Detector locally using `uv` and profiling your machine's environment for the first time.

### Prerequisites
* Python 3.11 or greater
* `uv` installed on your machine (`curl -LsSf https://astral.sh | sh`)

### Step 1: Clone and Set Up the Workspace
Navigate to your copy of the repository and synchronize the isolated development environment:
```bash
uv sync
```
This builds an editable package link mapped inside `.venv/` and pulls down all terminal dependencies (`typer`, `rich`, and `pyyaml`).

### Step 2: Run a Local Environment Discovery Action
Execute the script through your local terminal using the automatic virtualenv invocation shortcut:
```bash
uv run cloud-detect --include-runtime
```

### What You Just Learned
Because you executed this outside of a cluster or public cloud, your network metadata requests safely timed out after `1.0s`. The application printed a table layout showing `Unknown` for both layers, alongside a complete listing of verified infrastructure modules that were **definitively ruled out**.

---

## 2. How-To Guides (Goal-Oriented)

### How to Build and Run the App via Docker
To bake the application package into an unprivileged production container that defaults to structured JSON logging outputs:

```bash
# 1. Lock down dependency trees into a lockfile manifest
uv lock

# 2. Compile the container image
docker build -t cloud-detector:latest .

# 3. Spin up the container to verify output
docker run --rm cloud-detector:latest
```

### How to Override Default Output Formats
The tool allows you to change structural representations on the fly via the `-o` / `--output` enum parameter mapping (`json`, `yaml`, `table`, `csv`, `tsv`):

```bash
# Get pure multi-line YAML text logs to standard output
docker run --rm cloud-detector:latest --include-runtime -o yaml
```

### How to Save Analysis Streams to Disk
To direct verification pipelines out to flat files instead of polluting shell standard outputs, inject the `-f` / `--file` option argument:

```bash
uv run cloud-detect -r -o json -f cluster-audit.json
```
*(Status alerts pass directly through to `stderr` so that stdout data pipelines stay pristine during file writes.)*

### How to Deploy to MicroK8s or Upstream Kubernetes
Because default `kubectl run` engines force an external pull policy that might trigger rate limitations (`ImagePullBackOff`), pass an inline JSON override configuration string to leverage local container storage layers safely:

```bash
# 1. Sideload the local compilation archive directly into the MicroK8s storage ring
docker save cloud-detector:latest | microk8s ctr images import -

# 2. Fire the deployment stream with localized fallback policies and YAML formatting
kubectl run cloud-detector \
  --image=cloud-detector:latest \
  --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"cloud-detector","image":"cloud-detector:latest","imagePullPolicy":"IfNotPresent"}]}}' \
  -- --include-runtime -o yaml

# 3. Read the generated environment evaluation data
kubectl logs cloud-detector
```

---

## 3. Reference (Information-Oriented)

### Directory Structure
```text
cloud-detector/
├── Dockerfile          # Multi-stage production container manifest
├── pyproject.toml      # UV backend package configuration settings
├── uv.lock            # Frozen deterministic package dependency map
└── src/
    └── cloud_detector/
        ├── __init__.py # Module entry boundary hook
        ├── cli.py      # Typer wrapper and data presenting logic
        └── core.py     # Independent evaluation and scanning engine
```

### CLI Command Options
Execute `cloud-detect --help` or see the absolute options parameter truth table below:

| Parameter Flag | Alternate Short Flag | Input Enum Type | Default Value | Functional Scope Description |
| :--- | :--- | :--- | :--- | :--- |
| `--include-runtime` | `-r` | *Boolean* | `False` | Forces execution of container and orchestrator profiling layers. |
| `--output` | `-o` | `table \| json \| yaml \| csv \| tsv` | `table` *(CLI local)*<br>`json` *(Dockerfile default)* | Configures text rendering schemas returned to output channels. |
| `--file` | `-f` | *String File Path* | `None` | Redirects generated results data straight to disk storage files. |

### Core Library Return Contracts
The `cloud_detector.core.detect_all()` method exposes a programmatic data schema returned as a standard Python dictionary:
```json
{
  "infrastructure": "Unknown",
  "runtime": "Vanilla K8s (MicroK8s)",
  "exclusions": {
    "infrastructure": ["AWS", "Azure", "GCP", "OpenStack", "VCF"],
    "runtime": ["AKS", "Docker", "EKS", "GKE", "Magnum", "OCP (OpenShift)"]
  }
}
```

---

## 4. Explanation (Understanding-Oriented)

### Understanding the Metadata Discovery Boundary
Public clouds route configuration data over the link-local routing IP address `169.254.169.254`. When Cloud Detector triggers an inspection run, it performs asynchronous web calls over that address. 

To safeguard systems against network blockages or execution hanging inside firewalled container environments, the engine assigns an aggressive `1.0s` connection timeout limit. If a signature endpoint throws an error or exceeds that time slice, it is automatically categorized under the `exclusions` block.

```text
               ┌──────────────────────────────┐
               │    169.254.169.254 (IMDS)    │
               └──────────────┬───────────────┘
                              │
               ┌──────────────┴───────────────┐
               ▼                              ▼
      [Success Response]               [Timeout / Drop]
               │                              │
     Identified As: [Cloud]         Exclusions: [Not Cloud]
```

### Overcoming Container Isolation Boundaries
Standard container runtimes (such as Docker, Podman, and Kubernetes nodes) isolate hardware configuration states. Low-level host traits like `/sys/class/dmi/id/sys_vendor` are masked or unreachable from within unprivileged user namespaces.

To accurately detect local distributions like **MicroK8s** or **K3s** from inside a secure, unprivileged container pod, Cloud Detector relies on two main extraction methods:

1. **Environmental Footprint Injections:** It monitors standard runtime API server patterns (such as custom port flags like `:16443` or vendor environment variable names).
2. **Mount Table Interception:** It scans `/proc/self/mountinfo`. This file is completely accessible from inside unprivileged containers and explicitly leaks the host storage paths used by container engines (e.g. tracking host paths like `/snap/microk8s` or `/var/lib/rancher`). This provides fallback platform verification without needing elevated root user permissions or `hostPath` mount access hacks.
