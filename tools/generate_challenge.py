#!/usr/bin/env python3
import argparse, os, random, shutil, yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "challenges" / "templates"
OUT = ROOT / "challenges" / "rendered"
os.makedirs(OUT, exist_ok=True)

def yload(p): return yaml.safe_load(open(p))
def ydump(doc, p): open(p, "w").write(yaml.safe_dump(doc, sort_keys=False))

def copy_base():
    for name in ["ns.yaml", "app-deploy.yaml", "app-svc.yaml", "busybox.yaml", "pvc.yaml"]:
        shutil.copy2(TPL / name, OUT / name)

# ---- Fault injections (no stdout leaks) ----
def fault_service_selector_mismatch(deploy_doc, svc_doc):
    svc_doc["spec"]["selector"]["app"] = "appp"
    return deploy_doc, svc_doc

def fault_bad_readiness_probe(deploy_doc, svc_doc):
    cnt = deploy_doc["spec"]["template"]["spec"]["containers"][0]
    cnt["readinessProbe"]["httpGet"]["path"] = "/readyz"
    cnt["readinessProbe"]["initialDelaySeconds"] = 0
    cnt["readinessProbe"]["periodSeconds"] = 2
    return deploy_doc, svc_doc

def fault_targetport_mismatch(deploy_doc, svc_doc):
    svc_doc["spec"]["ports"][0]["targetPort"] = 8080
    return deploy_doc, svc_doc

def fault_default_deny_network_policy(ns_doc, deploy_doc, svc_doc):
    np = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "default-deny", "namespace": "kbox"},
        "spec": {"podSelector": {}, "policyTypes": ["Ingress","Egress"]},
    }
    ydump(np, OUT / "np.yaml")
    return deploy_doc, svc_doc

def fault_env_config_missing_key(deploy_doc):
    cnt = deploy_doc["spec"]["template"]["spec"]["containers"][0]
    cnt.setdefault("env", []).append({
        "name": "WELCOME_MSG",
        "valueFrom": {"configMapKeyRef": {"name": "app-config", "key": "welcome"}}
    })
    return deploy_doc

def fault_claimref_mismatch_in_deployment(deploy_doc):
    vols = deploy_doc["spec"]["template"]["spec"]["volumes"]
    for v in vols:
        if v.get("name") == "webroot" and "persistentVolumeClaim" in v:
            v["persistentVolumeClaim"]["claimName"] = "app-pvcc"  # subtle typo
    return deploy_doc

FAULTS = {
    "svc_selector_mismatch": fault_service_selector_mismatch,
    "bad_readiness_probe":   fault_bad_readiness_probe,
    "targetport_mismatch":   fault_targetport_mismatch,
    "default_deny_np":       fault_default_deny_network_policy,
    "claimref_mismatch":     fault_claimref_mismatch_in_deployment,
    "env_missing_key":       fault_env_config_missing_key,
}

OBJECTIVES = {
    "svc_selector_mismatch": "- Ensure the **Service** exposes at least 1 endpoint (check `kubectl get ep`).",
    "targetport_mismatch":   "- From `net-debug`, HTTP GET to `app.kbox.svc.cluster.local:80` should return **200 OK**.",
    "bad_readiness_probe":   "- All Pods for `app` reach **Ready** (readiness probe passes).",
    "default_deny_np":       "- In-cluster traffic from `net-debug` to `app:80` must **succeed** (no timeouts).",
    "claimref_mismatch":     "- Pods should **mount** the PVC successfully (no MountVolume errors).",
    "env_missing_key":       "- The `app` container should **start** without CrashLoopBackOff due to missing env/config.",
}

def pick_faults(difficulty, rng):
    keys = list(FAULTS.keys())
    return {"easy": rng.sample(keys,1), "medium": rng.sample(keys,2), "hard": rng.sample(keys,3)}[difficulty]

def write_brief(seed, difficulty, chosen):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# K8s in a Box — Scenario Brief",
        "",
        f"- Generated: `{now}`",
        f"- Difficulty: **{difficulty}**",
        f"- Seed: `{seed}`",
        "",
        "## Setup",
        "```bash",
        "make cluster",
        f"make challenge DIFFICULTY={difficulty} SEED={seed}",
        "make status",
        "```",
        "",
        "## Your Objective",
        "Bring the in-cluster service **app** to a healthy state and pass verification:",
        "",
        "```bash",
        "make verify",
        "```",
        "",
        "## Acceptance Criteria",
    ]
    for key in chosen:
        lines.append(OBJECTIVES[key])
    lines += [
        "- `kubectl get pvc -n kbox` shows **Bound** for `app-pvc`.",
        "- `kubectl get pods -n kbox` shows Pods **Ready**.",
        "- `kubectl get svc,ep -n kbox` shows **endpoints** for `app`.",
        "- From `net-debug`, `wget -qO- app.kbox.svc.cluster.local/health` returns **200 OK** (or `/`).",
        "",
        "## Hints (optional)",
        "- Compare labels and selectors between Deployment and Service.",
        "- Verify `targetPort` vs containerPort.",
        "- Check Events for probe or volume mount failures.",
        "- If traffic times out, consider NetworkPolicies.",
        "- Use `kubectl exec -n kbox -it net-debug -- sh` to curl/wget the service.",
    ]
    (OUT / "BRIEF.md").write_text("\n".join(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--difficulty", choices=["easy","medium","hard"], default="easy")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # reset render dir
    for f in OUT.glob("*"): f.unlink()

    copy_base()
    ns = yload(OUT/"ns.yaml")
    deploy = yload(OUT/"app-deploy.yaml")
    svc = yload(OUT/"app-svc.yaml")
    pvc = yload(OUT/"pvc.yaml")

    chosen = pick_faults(args.difficulty, rng)
    for key in chosen:
        if key == "env_missing_key":
            deploy = fault_env_config_missing_key(deploy)
        elif key == "default_deny_np":
            deploy, svc = fault_default_deny_network_policy(ns, deploy, svc)
        elif key == "svc_selector_mismatch":
            deploy, svc = fault_service_selector_mismatch(deploy, svc)
        elif key == "bad_readiness_probe":
            deploy, svc = fault_bad_readiness_probe(deploy, svc)
        elif key == "targetport_mismatch":
            deploy, svc = fault_targetport_mismatch(deploy, svc)
        elif key == "claimref_mismatch":
            deploy = fault_claimref_mismatch_in_deployment(deploy)

    ydump(ns, OUT/"ns.yaml")
    ydump(pvc, OUT/"pvc.yaml")
    ydump(deploy, OUT/"app-deploy.yaml")
    ydump(svc, OUT/"app-svc.yaml")

    write_brief(args.seed, args.difficulty, chosen)
    print(f"Challenge generated with seed {args.seed} at difficulty '{args.difficulty}'.")
    print("Manifests + BRIEF written to challenges/rendered/.")

if __name__ == "__main__":
    main()
