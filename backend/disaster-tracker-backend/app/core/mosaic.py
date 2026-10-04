import os

import rasterio
from rasterio.merge import merge
from rasterio.warp import transform_bounds


def build_mosaic(tile_paths: list[str], out_path: str, bounds: tuple[float, float, float, float]) -> str:
    """Ghép tile thành GeoTIFF phủ `bounds` (tây, nam, đông, bắc theo WGS84).

    Vùng không có tile phủ lên sẽ dùng giá trị nodata của tile nguồn.
    """
    if not tile_paths:
        raise ValueError("At least one tile is required to build a mosaic")

    with rasterio.open(tile_paths[0]) as first:
        profile = first.profile.copy()
        reference = {
            "crs": first.crs,
            "res": first.res,
            "dtype": first.dtypes,
            "count": first.count,
            "nodata": first.nodata,
        }

    for tile_path in tile_paths[1:]:
        with rasterio.open(tile_path) as tile:
            current = {
                "crs": tile.crs,
                "res": tile.res,
                "dtype": tile.dtypes,
                "count": tile.count,
                "nodata": tile.nodata,
            }
            # Rasterio.merge lấy profile của tile đầu tiên. Nếu tile khác lệch
            # lưới, kết quả có thể sai pixel hoặc sai tọa độ mà không báo.
            if current != reference:
                raise ValueError(f"Tile metadata is incompatible with {tile_paths[0]}: {tile_path}")

    data, transform = merge(
        tile_paths,
        bounds=transform_bounds("EPSG:4326", profile["crs"], *bounds),
        target_aligned_pixels=True,  # giữ lưới pixel nguồn, không resample
        nodata=reference["nodata"],
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
    if reference["nodata"] is not None:
        profile.update(nodata=reference["nodata"])

    # Ghi cạnh file đích rồi đổi tên nguyên tử để reader không thấy mosaic dở dang.
    partial = out_path + ".part"
    with rasterio.open(partial, "w", **profile) as dst:
        dst.write(data)
    os.replace(partial, out_path)
    return out_path
