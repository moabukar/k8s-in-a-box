#!/usr/bin/env python3
import argparse, os, random, shutil, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "challenges" / "templates"
OUT = ROOT / "challenges" / "rendered"
os.makedirs(OUT, exist_ok=True)

def yload(p): return yaml.safe_load(open(p))
def ydump(doc, p): open(p, "w").write(yaml.safe_dump(doc, sort_keys=False))

def copy_base():
    for name in ["ns.yaml", "app-deploy.yaml", "app-svc.yaml", "busybox.yaml", "pvc.yaml"]:
        shutil.copy2(TPL / name, OUT / name)

def fault_service_selector_mismatch(deploy_doc, svc_doc):
    svc_doc["spec"]["selector"]["app"] = "appp"; return deploy_doc, svc_doc

def fault_bad_readiness_probe(deploy_doc, svc_doc):
    cnt = deploy_doc["spec"]["template"]["spec"]["containers"][0]
    cnt["readinessProbe"]["httpGet"]["path"] = "/readyz"
    cnt["readinessProbe"]["initialDelaySeconds"] = 0
    cnt["readinessProbe"]["periodSeconds"] = 2
    return deploy_doc, svc_doc

def fault_targetport_mismatch(deploy_doc, svc_doc):
    svc_doc["spec"]["ports"][0]["targetPort"] = 8080; return deploy_doc, svc_doc

def fault_default_deny_network_policy(ns_doc, deploy_doc, svc_doc):
    np = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "default-deny", "namespace": "kbox"},
        "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
    }
    ydump(np, OUT / "np.yaml"); return deploy_doc, svc_doc

def fault_pvc_unknown_storageclass(pvc_doc):
    pvc_doc.setdefault("spec", {})["storageClassName"] = "fast"; return pvc_doc

def fault_env_config_missing_key(deploy_doc):
    cnt = deploy_doc["spec"]["template"]["spec"]["containers"][0]
    cnt.setdefault("env", []).append({"name": "WELCOME_MSG","valueFrom":{"configMapKeyRef":{"name":"app-config","key":"welcome"}}})
    return deploy_doc

FAULTS = {
    "svc_selector_mismatch": fault_service_selector_mismatch,
    "bad_readiness_probe": fault_bad_readiness_probe,
    "targetport_mismatch": fault_targetport_mismatch,
    "default_deny_np": fault_default_deny_network_policy,
    "pvc_unknown_sc": fault_pvc_unknown_storageclass,
    "env_missing_key": fault_env_config_missing_key,
}

def pick_faults(difficulty, rng):
    keys = list(FAULTS.keys())
    return {"easy": rng.sample(keys,1), "medium": rng.sample(keys,2), "hard": rng.sample(keys,3)}[difficulty]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--difficulty", choices=["easy","medium","hard"], default="easy")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    for f in OUT.glob("*"): f.unlink()
    copy_base()

    ns = yload(OUT/"ns.yaml")
    deploy = yload(OUT/"app-deploy.yaml")
    svc = yload(OUT/"app-svc.yaml")
    pvc = yload(OUT/"pvc.yaml")

    chosen = pick_faults(args.difficulty, rng)
    for key in chosen:
        if key == "pvc_unknown_sc": pvc = fault_pvc_unknown_storageclass(pvc)
        elif key == "env_missing_key": deploy = fault_env_config_missing_key(deploy)
        elif key == "default_deny_np": deploy, svc = fault_default_deny_network_policy(ns, deploy, svc)
        elif key == "svc_selector_mismatch": deploy, svc = fault_service_selector_mismatch(deploy, svc)
        elif key == "bad_readiness_probe": deploy, svc = fault_bad_readiness_probe(deploy, svc)
        elif key == "targetport_mismatch": deploy, svc = fault_targetport_mismatch(deploy, svc)

    ydump(ns, OUT/"ns.yaml"); ydump(pvc, OUT/"pvc.yaml"); ydump(deploy, OUT/"app-deploy.yaml"); ydump(svc, OUT/"app-svc.yaml")
    print(f"Challenge generated with seed {args.seed} at difficulty '{args.difficulty}'. Manifests in challenges/rendered/.")

if __name__ == "__main__":
    main()
