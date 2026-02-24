# SentinelX — Build Tooling
# Requires: tools/tailwindcss (standalone CLI binary)

TAILWIND := ./tools/tailwindcss
INPUT    := app/static/src/input.css
OUTPUT   := app/static/dist/style.css
PLATFORM := linux-x64

.PHONY: tailwind-install css css-watch build

## Download Tailwind standalone CLI binary
tailwind-install:
	@mkdir -p tools
	curl -sLo $(TAILWIND) \
		https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-$(PLATFORM)
	chmod +x $(TAILWIND)
	@echo "Tailwind CLI installed at $(TAILWIND)"

## Build CSS (one-shot)
css:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --minify

## Build CSS (watch mode for development)
css-watch:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --watch

## Full build
build: css
