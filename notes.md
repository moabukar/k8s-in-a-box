## Student flow

```bash
# 0) Pre-reqs running: Docker Desktop up, kind + kubectl installed
#    macOS: brew install kind kubernetes-cli

# 1) Clone repo
git clone https://github.com/moabukar/k8s-in-a-box && cd k8s-in-a-box

# 2) One-time local env
make setup

# (first time only) ensure scripts are executable (in case git perms stripped)
chmod +x hack/*.sh

# 3) Create cluster
make cluster

# 4) Generate + deploy a reproducible scenario
make challenge DIFFICULTY=medium SEED=424242

# 5) Read the brief (symptoms, acceptance criteria)
make brief

# 6) Inspect system
make status
kubectl -n kbox get pods,svc,ep
kubectl -n kbox describe deploy/app
kubectl -n kbox exec -it net-debug -- sh -c 'wget -S -qO- app.kbox.svc.cluster.local/health || true'

# 7) Iterate until green, then verify
make verify

```

## What you should see (typical)

- `make challenge … → “Challenge generated with seed 424242… Manifests + BRIEF written…”`
- `make brief → a small checklist (no spoilers).`

- `make verify:`
  - Initially may FAIL on step [2/4] Pods Ready? or [3/4] Service has endpoints? etc.
  - Once fixed → Verification passed.

## Clean up

```bash
make reset        # resets only the kbox namespace (keep cluster)
# or
make clean        # deletes the kind cluster
```

## Pre-commit hooks

```bash
# optional
pipx install pre-commit || pip install pre-commit
pre-commit install
pre-commit run --all-files
```
