SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
KUBECTL := hack/kubectl-wrap.sh
SEED ?= $(shell date +%s)
DIFFICULTY ?= easy   # easy|medium|hard

.PHONY: setup cluster delete-cluster challenge status hint verify reset clean cilium

setup:
	test -d .venv || python3 -m venv .venv
	$(PIP) install -U pip >/dev/null
	$(PIP) install -r requirements.txt

cluster:
	bash hack/kind.sh up

delete-cluster:
	bash hack/kind.sh down

challenge: # generate + apply randomised challenge
	$(PY) tools/generate_challenge.py --seed $(SEED) --difficulty $(DIFFICULTY)
	kubectl apply -f challenges/rendered/ns.yaml
	kubectl apply -f challenges/rendered/pvc.yaml || true
	kubectl apply -f challenges/rendered/app-deploy.yaml
	kubectl apply -f challenges/rendered/app-svc.yaml
	kubectl apply -f challenges/rendered/busybox.yaml

status:
	$(KUBECTL) -n kbox get pods,svc,ep
	@echo; echo "Events (last 60s):"; \
	$(KUBECTL) -n kbox get events --sort-by=.lastTimestamp | tail -n 50 || true

hint:
	bash hack/hints.sh

verify:
	bash hack/verify.sh

reset:
	-kubectl delete ns kbox --ignore-not-found
	@rm -rf challenges/rendered/*

clean: delete-cluster
	@rm -rf challenges/rendered/*

# Optional: Install Cilium (experimental). Requires cluster already up.
cilium:
	@echo "Installing Cilium via Helm..."
	helm repo add cilium https://helm.cilium.io >/dev/null
	helm repo update >/dev/null
	helm upgrade --install cilium cilium/cilium \
	  --namespace kube-system \
	  --set hubble.enabled=true \
	  --set hubble.relay.enabled=true \
	  --set hubble.ui.enabled=true
