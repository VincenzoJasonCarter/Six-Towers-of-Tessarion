# Six Towers of Tessarion — entry points for the three subprojects.
#
# Requires `uv` on PATH. Extra flags can be passed through ARGS, e.g.:
#   make dnd-sim ARGS="--seed 7 --quiet"
#   make map-segment ARGS="--zoom 6"
#
# This Makefile assumes a POSIX-ish shell (Git Bash, MSYS, WSL) runs the
# recipes, which is how `make` itself normally gets onto a Windows PATH.

.DEFAULT_GOAL := help
ARGS :=

# --- floor-generator (the root uv project: temporal floors, combat sim, world map) ---

.PHONY: sync
sync: ## Install/update dependencies for both uv projects
	uv sync
	uv sync --project crafting-dashboard

.PHONY: floor-generate
floor-generate: ## Generate a Thal'Vireth temporal floor (renders to floor-generator/output/)
	uv run floor-generator $(ARGS)

.PHONY: dnd-sim
dnd-sim: ## Simulate one 5e combat encounter on a temporal floor
	uv run dnd-sim $(ARGS)

.PHONY: dnd-gui
dnd-gui: ## Play one combat encounter interactively (Pygame window)
	uv run dnd-gui $(ARGS)

.PHONY: dnd-run
dnd-run: ## Run a full 10-floor tower climb
	uv run dnd-run $(ARGS)

.PHONY: map-segment
map-segment: ## Split the latest Azgaar .map in map/ into per-state mini maps
	uv run map-segmenter $(ARGS)

# --- crafting-dashboard (browser GUI for Ch.7-9 crafting/economy) ---

.PHONY: crafting-dashboard
crafting-dashboard: ## Launch the crafting dashboard at http://127.0.0.1:8765/
	uv run --project crafting-dashboard crafting-dashboard $(ARGS)

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
library-build: ## Export a static snapshot to library/library.html
	uv run library/build.py

# --- misc ---

.PHONY: help
help: ## List available commands
	@echo "Six Towers of Tessarion"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
