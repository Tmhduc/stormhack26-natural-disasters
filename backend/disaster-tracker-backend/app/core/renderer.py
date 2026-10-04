import numpy as np
from PIL import Image

FLOOD_RGB = (217, 0, 0)  # the red used by the map legend
MAX_SIDE = 1500  # px; the map never draws the overlay larger than this


def render_overlay_png(flood_mask: np.ndarray, output_path: str) -> str:
    """Render flood cells as a transparent PNG for the map overlay.

    The full raster (~7,300 x 7,900 cells) is shrunk to map size. Each PNG pixel is red
    if any raster cell it covers is flooded, so small floods stay visible. Working on
    8-bit data keeps this to ~100 MB; drawing it through matplotlib needed ~5.6 GB,
    which crashed small servers.
    """
    height, width = flood_mask.shape
    scale = min(1.0, MAX_SIDE / max(height, width))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    # BOX averages exactly the source area under each output pixel, so > 0 means "any flood".
    # The mask is 0/1 uint8 (see clipper); scaling it to 0/255 costs one 8-bit copy.
    shrunk = Image.fromarray(flood_mask.astype(np.uint8, copy=False) * np.uint8(255)).resize(size, Image.Resampling.BOX)
    overlay = Image.fromarray((np.asarray(shrunk) > 0).astype(np.uint8))  # 0 = clear, 1 = flood
    overlay.putpalette([0, 0, 0, *FLOOD_RGB])
    overlay.save(output_path, transparency=0, optimize=True)
    return output_path
