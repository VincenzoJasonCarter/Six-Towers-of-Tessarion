# ---------------------------------------------------------------
# Matplotlib rendering
# ---------------------------------------------------------------

import matplotlib.patheffects as patheffects
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .obstacles import DEFAULT_BLOCK_COLOR, DEFAULT_WALL_COLOR
from .progression import DOOR_COLOR, LADDER_COLOR, door_world_rect, ladder_world_rect
from .throne_room import STEP_COLOR
from .zones import zone_label


def render_floor(
    size, seed, zones, zone_types, entrance_door, exit_ladder, texture,
    obstacles=None, throne_steps=None, export_render=None, show=False,
):
    """Render the annotated floor: texture background, grid, zone
    outlines/labels, obstacles, throne steps, entrance door, exit
    ladder and legend.

    Saves to `export_render` if given, opens an interactive preview
    if `show` is True, and always closes the figure afterward.
    """

    obstacles = obstacles or {"walls": [], "blocks": []}
    throne_steps = throne_steps or []

    fig, ax = plt.subplots(figsize=(9, 9))

    ax.imshow(
        texture,
        extent=(0, size, 0, size),
        origin="lower",
        interpolation="bilinear",
        zorder=0,
    )

    # Floor boundary
    ax.add_patch(
        Rectangle(
            (0, 0),
            size,
            size,
            fill=False,
            linewidth=2,
            zorder=3,
        )
    )

    # Grid
    ax.set_xticks(range(size + 1))
    ax.set_yticks(range(size + 1))

    ax.grid(
        True,
        linewidth=0.5,
        alpha=0.25,
        color="white",
        zorder=1,
    )

    # -----------------------------------------------------
    # Temporal zones
    # -----------------------------------------------------

    seen_types = set()

    for zone in zones:

        x = zone["x"]
        y = zone["y"]
        w = zone["w"]
        h = zone["h"]
        zone_type = zone["type"]

        cfg = zone_types[zone_type]

        ax.add_patch(
            Rectangle(
                (x, y),
                w,
                h,
                fill=False,
                edgecolor=cfg["color"],
                linewidth=2.5,
                zorder=2,
                label=zone_type if zone_type not in seen_types else None,
            )
        )
        seen_types.add(zone_type)

        label = ax.text(
            x + w / 2,
            y + h / 2,
            zone_label(zone_type, cfg),
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=cfg["color"],
            zorder=4,
        )
        label.set_path_effects([
            patheffects.withStroke(linewidth=2.5, foreground="white")
        ])

    # -----------------------------------------------------
    # Obstacles: wall segments (on the tile edges, not filling a
    # tile) and the rarer full-tile blocks.
    # -----------------------------------------------------

    for i, wall in enumerate(obstacles["walls"]):
        ax.plot(
            [wall["x1"], wall["x2"]],
            [wall["y1"], wall["y2"]],
            color=DEFAULT_WALL_COLOR,
            linewidth=4,
            solid_capstyle="round",
            zorder=3.5,
            label="Wall" if i == 0 else None,
        )

    for i, block in enumerate(obstacles["blocks"]):
        ax.add_patch(
            Rectangle(
                (block["x"], block["y"]),
                block["w"],
                block["h"],
                facecolor=DEFAULT_BLOCK_COLOR,
                edgecolor="black",
                linewidth=1.5,
                hatch="xx",
                zorder=3.5,
                label="Obstacle" if i == 0 else None,
            )
        )

    # -----------------------------------------------------
    # Throne room: a boss floor's decorative stepped dais - purely
    # visual, not an obstacle (see throne_room.py), so it's drawn
    # thinner than a wall and never appears in obstacles["walls"].
    # -----------------------------------------------------

    for i, (x0, y0, x1, y1) in enumerate(throne_steps):
        ax.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fill=False,
                edgecolor=STEP_COLOR,
                linewidth=1.5,
                zorder=3.2,
                label="Throne Steps" if i == 0 else None,
            )
        )

    # -----------------------------------------------------
    # Entrance door / exit ladder
    # -----------------------------------------------------

    dx, dy, dw, dh = door_world_rect(entrance_door, size)

    ax.add_patch(
        Rectangle(
            (dx, dy), dw, dh,
            facecolor=DOOR_COLOR,
            edgecolor="black",
            linewidth=1,
            zorder=5,
            label="Entrance Door",
        )
    )

    lx, ly, lw, lh = ladder_world_rect(exit_ladder)

    ax.add_patch(
        Rectangle(
            (lx, ly), lw, lh,
            facecolor=LADDER_COLOR,
            edgecolor="black",
            linewidth=1.5,
            hatch="----",
            zorder=5,
            label="Exit Ladder",
        )
    )

    ladder_label = ax.text(
        lx + lw / 2,
        ly + lh / 2,
        "▲",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        zorder=6,
    )
    ladder_label.set_path_effects([
        patheffects.withStroke(linewidth=2, foreground="white")
    ])

    # -----------------------------------------------------
    # Formatting
    # -----------------------------------------------------

    ax.set_xlim(0, size)
    ax.set_ylim(0, size)

    ax.set_aspect("equal")

    ax.set_xlabel("Meters")
    ax.set_ylabel("Meters")

    ax.set_title(
        f"Thal'Vireth Temporal Floor\n"
        f"{size}×{size} m | Seed: {seed}"
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.04),
        ncol=len(labels),
    )

    plt.tight_layout()

    if export_render:
        fig.savefig(export_render, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)
