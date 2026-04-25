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
AUDIT_RUNNER     := python3 tools/optimization_audit.py
AUDIT_OUTPUT     := .gsd/milestones/M013/M013-AUDIT.md
AUDIT_TEMPLATE   := .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md

.PHONY: tailwind-install esbuild-install css css-watch js js-dev js-watch typecheck build verify-runtime-boundary verify-fast verify-deep verify audit-m013-template audit-m013

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
css:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --minify

## Build CSS (watch mode for development)
css-watch:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --watch

## Build JS bundle (production — minified IIFE, no source maps)
js:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--minify \
		--outfile=$(JS_OUT)

## Build JS bundle (development — unminified, inline source maps)
js-dev:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--outfile=$(JS_OUT)

## Build JS bundle (watch mode — recompiles on file change)
js-watch:
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

## Runtime-state boundary verification lane
verify-runtime-boundary:
	python3 -m pytest -q tests/test_runtime_state_boundary.py
	python3 -m pytest -q tests/test_runtime_state_boundary_git.py
	python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues

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
