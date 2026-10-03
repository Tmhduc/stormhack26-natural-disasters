import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np


def render_overlay_png(flood_mask: np.ndarray, output_path: str) -> str:
    cmap = ListedColormap([
        (0, 0, 0, 0),
        (0.85, 0, 0, 1),
    ])

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(flood_mask, cmap=cmap, interpolation="nearest")
    ax.axis("off")
    plt.savefig(
        output_path,
        transparent=True,
        bbox_inches="tight",
        pad_inches=0,
        dpi=150,
        facecolor="none",
    )
    plt.close()
    return output_path
