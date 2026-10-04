import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.core import downloader
from app.core.mosaic import build_mosaic


class _Response:
    status_code = 200
    headers = {"Content-Type": "image/tiff"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b"12"


class BackendRegressionTests(unittest.TestCase):
    def test_download_rejects_truncated_tile(self):
        tile = downloader.RemoteTile(
            tile="h28v07",
            name="MCDWD_L3_F2_NRT.A2026276.h28v07.061.tif",
            day=date(2026, 10, 3),
            size=4,
            mtime=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(downloader, "RAW_DIR", directory):
                with patch.object(downloader._session, "get", return_value=_Response()):
                    with self.assertRaises(downloader.LanceError):
                        downloader.download_tile(tile)
            self.assertFalse(Path(directory, "2026276", tile.name + ".part").exists())

    def test_mosaic_rejects_incompatible_tile_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory, "first.tif")
            second_path = Path(directory, "second.tif")
            profile = {
                "driver": "GTiff",
                "height": 2,
                "width": 2,
                "count": 1,
                "dtype": "uint8",
                "crs": "EPSG:4326",
                "transform": from_origin(0, 2, 1, 1),
            }
            with rasterio.open(first_path, "w", **profile) as dataset:
                dataset.write(np.zeros((1, 2, 2), dtype=np.uint8))
            profile["dtype"] = "uint16"
            with rasterio.open(second_path, "w", **profile) as dataset:
                dataset.write(np.zeros((1, 2, 2), dtype=np.uint16))

            with self.assertRaises(ValueError):
                build_mosaic(
                    [str(first_path), str(second_path)],
                    str(Path(directory, "mosaic.tif")),
                    (0, 0, 2, 2),
                )


if __name__ == "__main__":
    unittest.main()