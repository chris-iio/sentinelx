# SentinelX — Build Tooling
# Requires: tools/tailwindcss (standalone CLI binary)
#           tools/esbuild     (standalone CLI binary)

TAILWIND         := ./tools/tailwindcss
ESBUILD          := ./tools/esbuild
INPUT            := app/static/src/input.css
OUTPUT           := app/static/dist/style.css
JS_ENTRY         := app/static/src/ts/main.ts
JS_OUT           := app/static/dist/main.js
PLATFORM         := linux-x64
ESBUILD_VERSION  := 0.27.3
DEV_SERVER       := python3 tools/dev_server.py
AUDIT_RUNNER     := python3 tools/optimization_audit.py
AUDIT_OUTPUT     := .gsd/milestones/M013/M013-AUDIT.md
AUDIT_TEMPLATE   := .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md

.PHONY: tailwind-install esbuild-install css css-watch js js-dev js-watch typecheck build dev-server-start dev-server-status dev-server-restart dev-server-stop repair-runtime-state verify-runtime-boundary verify-fast verify-deep verify audit-m013-template audit-m013

$(TAILWIND):
	$(MAKE) tailwind-install

$(ESBUILD):
	$(MAKE) esbuild-install

## Download Tailwind standalone CLI binary
tailwind-install:
	@mkdir -p tools
	curl -sLo $(TAILWIND) \
		https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-$(PLATFORM)
	chmod +x $(TAILWIND)
	@echo "Tailwind CLI installed at $(TAILWIND)"

## Download esbuild standalone binary
esbuild-install:
	@mkdir -p tools
	curl -sLo /tmp/esbuild.tgz \
		https://registry.npmjs.org/@esbuild/$(PLATFORM)/-/$(PLATFORM)-$(ESBUILD_VERSION).tgz
	tar xzf /tmp/esbuild.tgz -C /tmp
	mv /tmp/package/bin/esbuild $(ESBUILD)
	chmod +x $(ESBUILD)
	rm -rf /tmp/esbuild.tgz /tmp/package
	@echo "esbuild $(ESBUILD_VERSION) installed at $(ESBUILD)"

## Build CSS (one-shot)
css: $(TAILWIND)
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --minify

## Build CSS (watch mode for development)
css-watch: $(TAILWIND)
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --watch

## Build JS bundle (production — minified IIFE, no source maps)
js: $(ESBUILD)
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--minify \
		--outfile=$(JS_OUT)

## Build JS bundle (development — unminified, inline source maps)
js-dev: $(ESBUILD)
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--outfile=$(JS_OUT)

## Build JS bundle (watch mode — recompiles on file change)
js-watch: $(ESBUILD)
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--watch \
		--outfile=$(JS_OUT)

## Type-check TypeScript without emitting output
typecheck:
	npx tsc --noEmit

## Full build (CSS + JS)
build: css js

## Supported local dev-server start loop (wrapper over tools/dev_server.py)
dev-server-start:
	$(DEV_SERVER) start --format text

## Supported local dev-server inspection loop (wrapper over tools/dev_server.py)
dev-server-status:
	$(DEV_SERVER) status --format text

## Supported local dev-server restart loop (wrapper over tools/dev_server.py)
dev-server-restart:
	$(DEV_SERVER) restart --format text

## Supported local dev-server shutdown loop (wrapper over tools/dev_server.py)
dev-server-stop:
	$(DEV_SERVER) stop --format text

## Runtime-state repair lane (mutates supported transient findings, then re-audits blockers)
repair-runtime-state:
	python3 tools/runtime_state_repair.py --format text
	python3 tools/runtime_state_boundary.py audit --format text --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root

## Runtime-state boundary verification lane
verify-runtime-boundary:
	python3 -m pytest -q tests/test_runtime_state_boundary.py
	python3 -m pytest -q tests/test_runtime_state_boundary_git.py
	python3 tools/runtime_state_boundary.py audit --format text --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root

## Fast verification lane (non-E2E pytest + frontend checks + build)
verify-fast:
	python3 -m pytest -q -m 'not e2e'
	npx vitest run
	npx tsc --noEmit
	$(MAKE) build

## Deep verification lane (browser E2E only)
verify-deep:
	python3 -m pytest -q tests/e2e

## Full verification (fast lane + deep lane)
verify:
	$(MAKE) verify-fast
	$(MAKE) verify-deep

## Write the reusable M013 audit template scaffold

audit-m013-template:
	$(AUDIT_RUNNER) --mode template --output $(AUDIT_TEMPLATE)

## Write the current M013 audit artifact scaffold/baseline

audit-m013:
	$(AUDIT_RUNNER) --mode baseline --output $(AUDIT_OUTPUT)
