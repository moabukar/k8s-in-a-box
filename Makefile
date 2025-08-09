SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
KUBECTL := hack/kubectl-wrap.sh

SEED ?= $(shell date +%s)
DIFFICULTY ?= easy   # easy|medium|hard

.PHONY: setup init cluster delete-cluster challenge status hint verify brief reset clean teacher-answers

setup:
	test -d .venv || python3 -m venv .venv
	$(PIP) install -U pip >/dev/null
	$(PIP) install -r requirements.txt
	@# ensure scripts are executable (macOS sometimes strips bits)
	chmod +x hack/*.sh || true

cluster:
	bash hack/kind.sh up

delete-cluster:
	bash hack/kind.sh down

challenge: ## generate + apply randomised challenge
	$(PY) tools/generate_challenge.py --seed $(SEED) --difficulty $(DIFFICULTY)
	kubectl apply -f challenges/rendered/ns.yaml
	kubectl apply -f challenges/rendered/pvc.yaml || true
	kubectl apply -f challenges/rendered/app-deploy.yaml
	kubectl apply -f challenges/rendered/app-svc.yaml
	kubectl apply -f challenges/rendered/busybox.yaml

status:
	$(KUBECTL) -n kbox get pods,svc,ep
	@echo; echo "Recent events:"; \
	$(KUBECTL) -n kbox get events --sort-by=.lastTimestamp | tail -n 50 || true

hint:
	bash hack/hints.sh

verify:
	bash hack/verify.sh

brief:
	@test -f challenges/rendered/BRIEF.md && cat challenges/rendered/BRIEF.md || \
	( echo "No brief found. Run 'make challenge' first."; exit 1 )

reset:
	-kubectl delete ns kbox --ignore-not-found
	@rm -rf challenges/rendered/*

clean: delete-cluster
	@rm -rf challenges/rendered/*
