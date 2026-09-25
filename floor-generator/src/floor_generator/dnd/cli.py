# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

import argparse

from .combat import simulate_combat


def main():

    parser = argparse.ArgumentParser(
        description="Simulate a 5e combat encounter on a Thal'Vireth temporal floor."
    )

    parser.add_argument("--character", default=None, help="Path to a character YAML config (defaults to Pijo).")
    parser.add_argument("--seed", type=int, default=42, help="Seed for monster generation and combat rolls.")
    parser.add_argument("--floor-seed", type=int, default=None, help="Seed for the battlefield layout (defaults to --seed).")
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--quiet", action="store_true", help="Suppress the round-by-round log.")

    args = parser.parse_args()

    simulate_combat(
        character_path=args.character,
        seed=args.seed,
        floor_seed=args.floor_seed,
        max_rounds=args.max_rounds,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
