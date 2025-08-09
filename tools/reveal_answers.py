#!/usr/bin/env python3
"""
Teacher-only inspector: compares rendered vs templates and prints
the actual injected faults + concrete fixes.

Usage:
  I_AM_TEACHER=yes make teacher-answers SEED=... DIFFICULTY=...
"""
import argparse, yaml
from pathlib import Path

def yload(p):
    p = Path(p)
    return yaml.safe_load(p.read_text()) if p.exists() else None

def detect_faults(tpl_dir: Path, ren_dir: Path):
    faults = []
    dep = yload(ren_dir/"app-deploy.yaml")
    svc = yload(ren_dir/"app-svc.yaml")
    np  = yload(ren_dir/"np.yaml")

    # selector mismatch
    try:
        lab = dep["spec"]["template"]["metadata"]["labels"]["app"]
        sel = svc["spec"]["selector"]["app"]
        if lab != sel:
            faults.append(("svc_selector_mismatch",
                           "Service selector does not match Pod labels.",
                           [
                            "Fix Service selector to match Pod labels:",
                            "  kubectl -n kbox patch svc app --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/selector/app\",\"value\":\"app\"}]'",
                           ]))
    except Exception:
        pass

    # targetPort mismatch
    try:
        cport = dep["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"]
        tport = svc["spec"]["ports"][0]["targetPort"]
        if str(tport) != str(cport):
            faults.append(("targetport_mismatch",
                           f"Service targetPort ({tport}) != containerPort ({cport}).",
                           [
                            "Set Service targetPort to container's port (80):",
                            "  kubectl -n kbox patch svc app --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/ports/0/targetPort\",\"value\":80}]'",
                           ]))
    except Exception:
        pass

    # readiness probe bad path/timing
    try:
        rp = dep["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]
        path = rp["httpGet"]["path"]; delay = rp.get("initialDelaySeconds", 0)
        if path != "/health" or delay < 1:
            faults.append(("bad_readiness_probe",
                           f"Readiness probe is misconfigured (path='{path}', delay={delay}).",
                           [
                            "Patch readiness probe to a valid path and sensible delays:",
                            "  kubectl -n kbox patch deploy app --type='json' -p='[",
                            "    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/readinessProbe/httpGet/path\",\"value\":\"/health\"},",
                            "    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/readinessProbe/initialDelaySeconds\",\"value\":2},",
                            "    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/readinessProbe/periodSeconds\",\"value\":5}",
                            "  ]'",
                           ]))
    except Exception:
        pass

    # default deny NP
    if np and np.get("kind") == "NetworkPolicy" and np.get("spec", {}).get("podSelector", {}) == {}:
        faults.append(("default_deny_np",
                       "Default-deny NetworkPolicy blocks traffic.",
                       [
                        "Allow ingress to app from same namespace:",
                        "  kubectl -n kbox apply -f - <<'YAML'",
                        "  apiVersion: networking.k8s.io/v1",
                        "  kind: NetworkPolicy",
                        "  metadata: { name: allow-same-ns }",
                        "  spec:",
                        "    podSelector: { matchLabels: { app: app } }",
                        "    ingress:",
                        "    - from: [ { podSelector: {} } ]",
                        "      ports: [ { protocol: TCP, port: 80 } ]",
                        "  YAML",
                       ]))

    # claimref mismatch in Deployment
    try:
        vols = dep["spec"]["template"]["spec"]["volumes"]
        for v in vols:
            if v.get("name")=="webroot" and "persistentVolumeClaim" in v:
                claim = v["persistentVolumeClaim"]["claimName"]
                if claim != "app-pvc":
                    faults.append(("claimref_mismatch",
                                   f"Deployment mounts claimName '{claim}' but PVC is 'app-pvc'.",
                                   [
                                    "Fix Deployment volume claimName to 'app-pvc' and rollout:",
                                    "  kubectl -n kbox patch deploy app --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/template/spec/volumes/0/persistentVolumeClaim/claimName\",\"value\":\"app-pvc\"}]'",
                                   ]))
                    break
    except Exception:
        pass

    # env missing config
    try:
        env = dep["spec"]["template"]["spec"]["containers"][0].get("env", [])
        has_missing = any(e.get("valueFrom", {}).get("configMapKeyRef", {}).get("name")=="app-config" for e in env)
        if has_missing:
            faults.append(("env_missing_key",
                           "Container expects ConfigMap key that doesn't exist.",
                           [
                            "Create the expected ConfigMap key or remove the envRef:",
                            "  kubectl -n kbox create configmap app-config --from-literal=welcome='hello' --dry-run=client -o yaml | kubectl apply -f -",
                           ]))
    except Exception:
        pass

    return faults

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates-dir", required=True)
    ap.add_argument("--rendered-dir", required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--difficulty", required=True)
    args = ap.parse_args()

    ren = Path(args.rendered_dir)
    faults = detect_faults(Path(args.templates_dir), ren)

    print(f"# Teacher Answers — seed {args.seed}, difficulty {args.difficulty}\n")
    if not faults:
        print("_No faults detected (did you run `make challenge`?)_")
        return

    print("## Detected Faults & Fixes\n")
    for key, desc, fixes in faults:
        print(f"### {key}")
        print(f"- **Issue:** {desc}")
        print("- **Fix:**")
        for line in fixes:
            print(f"  {line}")
        print()

    print("## Quick Verification")
    print("```bash")
    print("make verify")
    print("```")

if __name__ == "__main__":
    main()
