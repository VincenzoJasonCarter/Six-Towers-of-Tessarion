# Six Towers of Tessarion — entry points for the subprojects (or `make hub` for all of them).
#
# Requires `uv` on PATH. Extra flags can be passed through ARGS, e.g.:
#   make library ARGS="--port 9000 --no-browser"
#
# This Makefile assumes a POSIX-ish shell (Git Bash, MSYS, WSL) runs the
# recipes, which is how `make` itself normally gets onto a Windows PATH.

.DEFAULT_GOAL := help
ARGS :=

# --- bestiary (Threadmint Bestiary encyclopedia, built from data/enemies.yaml) ---

.PHONY: bestiary
bestiary: ## Serve the bestiary live at http://127.0.0.1:8766/ (reloads on enemies.yaml edits)
	uv run bestiary/serve.py $(ARGS)

.PHONY: bestiary-build
bestiary-build: ## Export a static snapshot to bestiary/bestiary.html
	uv run bestiary/build.py

# --- library (the lore-book as a bookshelf of readable books) ---

.PHONY: library
library: ## Serve the lore library live at http://127.0.0.1:8767/ (reloads on chapter edits)
	uv run library/serve.py $(ARGS)

.PHONY: library-build
library-build: ## Export a static site to library/site/ (ARGS="--single-file" for one library.html)
	uv run library/build.py $(ARGS)

# --- barracks (charasheet, the character sheets; building it needs Node) ---

.PHONY: barracks
barracks: ## Serve the character sheets at http://127.0.0.1:8768/barracks/ (rebuilds first if charasheet/ changed)
	uv run barracks/serve.py $(ARGS)

.PHONY: barracks-build
barracks-build: ## Build charasheet for /barracks/ into charasheet/dist/ (ARGS="--force" to rebuild regardless)
	uv run barracks/build.py $(ARGS)

.PHONY: barracks-dev
barracks-dev: ## Work on charasheet's code: Vite's dev server with live reload at http://127.0.0.1:5173/
	cd charasheet && { test -d node_modules || npm ci --no-audit --no-fund; } && npm run dev -- --host 127.0.0.1 $(ARGS)

# --- memoria (the museum of Tessarion's history, a 3D building, from data/memoria.yaml) ---

.PHONY: memoria
memoria: ## Serve the Memoria live at http://127.0.0.1:8769/ (reloads on memoria.yaml edits)
	uv run memoria/serve.py $(ARGS)

.PHONY: memoria-build
memoria-build: ## Export a static snapshot to memoria/memoria.html
	uv run memoria/build.py

# --- arena (Monte Carlo power rankings for the subclasses) ---

.PHONY: arena
arena: ## Simulate the subclasses one-on-one and write arena/report.md (ARGS="--n 200" for a quick run)
	uv run arena/run.py $(ARGS)

.PHONY: arena-party
arena-party: ## Simulate every four-subclass party and write arena/party_report.md (ARGS="--n 50" for a quick run)
	uv run arena/party.py $(ARGS)

.PHONY: arena-evolution
arena-evolution: ## Simulate the Ascendant/Corrupted evolution branches and write arena/evolution_report.md (ARGS="--n 4" for a quick run)
	uv run arena/evolve.py $(ARGS)

# --- boss_brain (the boss brain and its research harness; needs Node 22.18+) ---

.PHONY: boss-brain-test
boss-brain-test: ## Type-check and unit-test the boss brain
	cd boss_brain && { test -d node_modules || npm ci --no-audit --no-fund; } && npm run check && npm test

.PHONY: boss-table
boss-table: ## Build the DM's table tool (one offline HTML file, DM-only, not on the public site) and open it
	cd boss_brain && { test -d node_modules || npm ci --no-audit --no-fund; } && npm run table:build && uv run --no-project python -c "import pathlib, webbrowser; webbrowser.open(pathlib.Path('table/dist/boss-table.html').resolve().as_uri())"

.PHONY: boss-brain-harness
boss-brain-harness: ## Score the boss brain against synthetic players → boss_brain/reports/ (ARGS="--trials 200" for a quick run)
	cd boss_brain && node src/harness/cli.ts $(ARGS)

# --- web (the hub, library, bestiary, barracks and memoria as one static site, for Vercel or any static host) ---

.PHONY: web-build
web-build: ## Build the public site (hub + library + bestiary + barracks + memoria) to dist/
	uv run web/build.py

# --- hub (one page for all of them) ---

.PHONY: hub
hub: ## Open everything in one place at http://127.0.0.1:8760/ (starts the library, bestiary, barracks and memoria)
	uv run hub/serve.py $(ARGS)

# --- misc ---

.PHONY: help
help: ## List available commands
	@echo "Six Towers of Tessarion"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
