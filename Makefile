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

.PHONY: tailwind-install esbuild-install css css-watch js js-dev js-watch typecheck build

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
	tsc --noEmit

## Full build (CSS + JS)
build: css js
