import os

import rasterio
from rasterio.merge import merge
from rasterio.warp import transform_bounds


def build_mosaic(tile_paths: list[str], out_path: str, bounds: tuple[float, float, float, float]) -> str:
    """Stitch the tiles into one GeoTIFF covering `bounds` (west, south, east, north in WGS84).

    Areas no tile covers get the tiles' nodata value (255, "insufficient data").
    """
    with rasterio.open(tile_paths[0]) as first:
        profile = first.profile

    data, transform = merge(
        tile_paths,
        bounds=transform_bounds("EPSG:4326", profile["crs"], *bounds),
        target_aligned_pixels=True,  # stay on the tiles' pixel grid, no resampling
    )
    profile.update(
        driver="GTiff",
        height=data.shape[1],
        width=data.shape[2],
        transform=transform,
        compress="deflate",
        tiled=True,
        blockxsize=512,
        blockysize=512,
    )

    # Write next to the target and swap it in, so readers never see a half-written mosaic.
    partial = out_path + ".part"
    with rasterio.open(partial, "w", **profile) as dst:
        dst.write(data)
    os.replace(partial, out_path)
    return out_path
