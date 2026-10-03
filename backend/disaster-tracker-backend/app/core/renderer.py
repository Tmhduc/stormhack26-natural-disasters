import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np


def render_overlay_png(flood_mask: np.ndarray, output_path: str) -> str:
    """Render các ô ngập thành PNG trong suốt để chồng lên bản đồ."""
    # Ô không ngập được để trong suốt để basemap hoặc boundary vẫn nhìn thấy
    # bên dưới các ô ngập màu đỏ ở frontend.
    cmap = ListedColormap([
        (0, 0, 0, 0),
        (0.85, 0, 0, 1),
    ])

    fig, ax = plt.subplots(figsize=(10, 10))
    # Giữ nguyên hướng của array để ảnh khớp với bounds và quy ước row/column
    # được sử dụng khi inspect một điểm.
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
