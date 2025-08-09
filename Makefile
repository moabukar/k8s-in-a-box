SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
KUBECTL := hack/kubectl-wrap.sh

SEED ?= $(shell date +%s)
DIFFICULTY ?= easy   # easy|medium|hard

SCENARIO_DIR := challenges/rendered
SCENARIO_FILE := $(SCENARIO_DIR)/.scenario

.PHONY: setup cluster delete-cluster sc-default challenge status hint verify brief reset clean teacher-answers answers

doctor:
	@echo "Repo: $$(pwd)"
	@echo -n "Docker: "; docker --version || true
	@echo -n "kind:   "; kind --version || true
	@echo -n "kubectl:"; kubectl version --client --output=yaml || true
	@echo -n "Python: "; python3 -V || true
	@test -d .venv || echo "NOTE: .venv missing (run: make setup)"
	@.venv/bin/python -c "import yaml; print('PyYAML OK')" 2>/dev/null || echo "PyYAML missing (run: make setup)"


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

# Ensure default SC even if cluster wasn't created via our script
sc-default:
	@kubectl get sc >/dev/null 2>&1 || true
	kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml >/dev/null
	kubectl annotate sc local-path storageclass.kubernetes.io/is-default-class=true --overwrite >/dev/null || true

challenge: sc-default
	$(PY) tools/generate_challenge.py --seed $(SEED) --difficulty $(DIFFICULTY)
	@printf "SEED=%s\nDIFFICULTY=%s\n" "$(SEED)" "$(DIFFICULTY)" > $(SCENARIO_FILE)
	kubectl apply -f $(SCENARIO_DIR)/ns.yaml
	kubectl apply -f $(SCENARIO_DIR)/pvc.yaml
	kubectl apply -f $(SCENARIO_DIR)/app-deploy.yaml
	kubectl apply -f $(SCENARIO_DIR)/app-svc.yaml
	kubectl apply -f $(SCENARIO_DIR)/busybox.yaml

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

# ------- Teacher-only (reads .scenario if you didn't pass SEED/DIFFICULTY) -------
teacher-answers:
	@if [[ "$$I_AM_TEACHER" != "yes" ]]; then \
		echo "Refusing: set I_AM_TEACHER=yes to continue."; \
		exit 2; \
	fi
	@test -f tools/reveal_answers.py || { echo "Missing tools/reveal_answers.py"; exit 3; }
	@SEED_EFF="$${SEED}"; DIFF_EFF="$${DIFFICULTY}"; \
	if [[ -f "$(SCENARIO_FILE)" ]]; then \
	  SF_SEED=$$(awk -F= '/^SEED=/{print $$2}' "$(SCENARIO_FILE)"); \
	  SF_DIFF=$$(awk -F= '/^DIFFICULTY=/{print $$2}' "$(SCENARIO_FILE)"); \
	  SEED_EFF="$${SEED_EFF:-$${SF_SEED}}"; \
	  DIFF_EFF="$${DIFF_EFF:-$${SF_DIFF}}"; \
	fi; \
	mkdir -p .teacher; \
	echo "Using seed=$${SEED_EFF} difficulty=$${DIFF_EFF}"; \
	$(PY) tools/reveal_answers.py \
	  --rendered-dir $(SCENARIO_DIR) \
	  --templates-dir challenges/templates \
	  --seed "$${SEED_EFF}" --difficulty "$${DIFF_EFF}" > ".teacher/answers-$${SEED_EFF}.md"; \
	echo "Wrote .teacher/answers-$${SEED_EFF}.md"

# Convenience alias (you typed `make answers` earlier)
answers: teacher-answers

#### Submissions ####

EVIDENCE_FILE ?= evidence-$(SEED).txt
SUBMIT_FILE ?= submission-$(SEED).zip

evidence:
	@echo "# Evidence ($(shell date -u +'%Y-%m-%dT%H:%M:%SZ'))" > $(EVIDENCE_FILE)
	@echo "Seed: $(SEED), Difficulty: $(DIFFICULTY)" >> $(EVIDENCE_FILE)
	@echo "\n== make verify ==" >> $(EVIDENCE_FILE) || true
	- bash hack/verify.sh >> $(EVIDENCE_FILE) 2>&1 || true
	@echo "\n== kubectl summary ==" >> $(EVIDENCE_FILE)
	- kubectl -n kbox get pods,svc,ep >> $(EVIDENCE_FILE) 2>&1 || true
	@echo "\n== events (last 50) ==" >> $(EVIDENCE_FILE)
	- kubectl -n kbox get events --sort-by=.lastTimestamp | tail -n 50 >> $(EVIDENCE_FILE) 2>&1 || true
	@echo "\n== brief ==" >> $(EVIDENCE_FILE)
	- cat challenges/rendered/BRIEF.md >> $(EVIDENCE_FILE) 2>/dev/null || true
	@echo "Wrote $(EVIDENCE_FILE)"

submit: evidence
	@zip -q $(SUBMIT_FILE) $(EVIDENCE_FILE) challenges/rendered/BRIEF.md || zip -q $(SUBMIT_FILE) $(EVIDENCE_FILE)
	@echo "Wrote $(SUBMIT_FILE) — upload this in Skool."
