# Backend Flow

Tài liệu này giải thích cách backend Vietnam Flood Monitor nhận input, xử lý dữ liệu và trả output cho frontend.

## 1. Tổng quan

Backend dùng FastAPI để cung cấp API phân tích dữ liệu ngập lụt của Việt Nam.

```text
NASA flood raster + Vietnam boundary + NASA token
                         |
                         v
                  FastAPI backend
                         |
             Cắt raster theo Việt Nam
                         |
                         v
                    Flood mask
                 1 = ngập, 0 = không ngập
                         |
          +--------------+--------------+
          |                             |
          v                             v
    Tính metrics                    Render PNG
          |                             |
          +--------------+--------------+
                         v
                       Cache
                         |
                         v
                     Frontend
```

## 2. Input của backend

### 2.1. Flood raster

Raster flood được lưu tại:

```text
data/vietnam_flood.tif
```

File này được tải từ NASA bằng các giá trị cấu hình trong `app/config.py`:

```python
TILE_ID = "h28v07"
YEAR = "2026"
DOY = "276"
```

Các giá trị này được dùng để tạo tên file và URL tải dữ liệu NASA.

### 2.2. NASA token

Token được lưu local tại:

```text
data/.token
```

Token được dùng trong request từ backend đến NASA:

```text
Authorization: Bearer <NASA_TOKEN>
```

Token không được gửi xuống frontend và không được commit vào Git.

### 2.3. Vietnam boundary

Boundary shapefile nằm tại:

```text
data/vietnam_boundary/vnm_admin0.shp
```

Các file đi kèm cần có:

```text
vnm_admin0.shp
vnm_admin0.shx
vnm_admin0.dbf
vnm_admin0.prj
vnm_admin0.cpg
```

Boundary dùng để cắt raster, chỉ giữ lại vùng Việt Nam.

## 3. Khởi động ứng dụng

File khởi động chính là:

```text
app/main.py
```

Chạy backend bằng:

```bash
cd backend/disaster-tracker-backend
uv run uvicorn app.main:app --reload
```

Khi start, app thực hiện:

1. Tạo FastAPI app.
2. Cấu hình CORS cho frontend local.
3. Tạo thư mục `cache/` nếu chưa tồn tại.
4. Mount `cache/` vào URL `/static`.
5. Đăng ký health route.
6. Đăng ký flood routes.

Overlay PNG có thể được truy cập qua:

```text
/static/flood_overlay.png
```

## 4. Flow xử lý metrics

Frontend gọi:

```http
GET /api/flood/metrics
```

Flow chi tiết:

```text
GET /api/flood/metrics
          |
          v
routes/flood.py:get_metrics()
          |
          v
core/cache.py:get_or_build()
          |
          +-- Đủ 3 file cache? -- Có --> Đọc JSON và trả kết quả
          |                              
          |                              +--> metrics.json
          |                              +--> bounds.json
          |                              +--> flood_overlay.png
          |
          +-- Chưa đủ ----------------> load_clipped_flood()
                                         |
                                         v
                                  Cắt raster Việt Nam
                                         |
                                         v
                                   Tạo flood mask
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
                 compute_metrics()                 render_overlay_png()
                       |                                   |
                       v                                   v
                  metrics.json                    flood_overlay.png
                                         |
                                         v
                                     bounds.json
```

### 4.1. Đọc và cắt raster

`app/core/clipper.py` thực hiện:

1. Đọc boundary bằng GeoPandas.
2. Đọc raster bằng Rasterio.
3. Chuyển boundary sang CRS của raster.
4. Dùng `rasterio.mask.mask()` để crop raster theo boundary Việt Nam.
5. Lấy band đầu tiên của raster.

### 4.2. Tạo flood mask

Raster source được chuyển thành binary mask:

```python
flood_mask = (data == FLOOD_VALUE).astype(np.uint8)
```

Trong đó:

```text
FLOOD_VALUE = 3
```

Kết quả:

```text
Giá trị raster = 3  ->  1 -> ngập
Giá trị khác 3     ->  0 -> không ngập
```

### 4.3. Tính metrics

`app/core/cache.py` đếm số pixel ngập:

```python
flood_pixels = int(flood_mask.sum())
```

Sau đó tính diện tích:

```python
flooded_km2 = flood_pixels * PIXEL_KM2
```

Hiện tại:

```python
PIXEL_KM2 = 0.0625
```

Output nội bộ:

```json
{
  "flood_pixels": 12345,
  "flooded_km2": 771.56
}
```

## 5. Flow tạo overlay PNG

`app/core/renderer.py` nhận `flood_mask` và tạo:

```text
cache/flood_overlay.png
```

Quy ước màu:

```text
Ô không ngập -> trong suốt
Ô ngập       -> màu đỏ
```

Ảnh được tạo trong suốt để frontend có thể chồng lên bản đồ hoặc boundary.

Ảnh PNG không tự chứa thông tin latitude/longitude. Vì vậy API trả thêm `bounds` để frontend biết vị trí đặt ảnh.

## 6. Cache

Backend dùng 3 file cache:

```text
cache/flood_overlay.png
cache/metrics.json
cache/bounds.json
```

Nếu cả 3 file tồn tại, backend đọc lại cache để tránh xử lý raster nhiều lần.

Nếu thiếu một file, backend build lại toàn bộ:

1. Load raster.
2. Crop theo boundary.
3. Tạo flood mask.
4. Tính metrics.
5. Render overlay.
6. Ghi lại 3 file cache.

### 6.1. Xóa cache

Khi gọi refresh, backend gọi:

```python
cache.invalidate()
```

Hàm này xóa các output cũ. Request tiếp theo sẽ build lại dữ liệu từ raster mới.

## 7. Các API hiện tại

### Health

```http
GET /api/health
```

Response:

```json
{
  "status": "ok"
}
```

Đây là liveness check. Nó chỉ xác nhận FastAPI đang chạy, chưa xác nhận raster, boundary, token hoặc cache đã sẵn sàng.

### Metrics

```http
GET /api/flood/metrics
```

Response mẫu:

```json
{
  "flood_pixels": 12345,
  "flooded_km2": 771.56,
  "bounds": [102.1, 8.4, 109.5, 23.4],
  "tile_id": "h28v07",
  "date": "2026-276",
  "last_updated": "2026-10-03T12:30:00"
}
```

`bounds` có thứ tự:

```text
[left, bottom, right, top]
```

### Overlay

```http
GET /api/flood/overlay
```

Response:

```json
{
  "png_url": "/static/flood_overlay.png",
  "bounds": [102.1, 8.4, 109.5, 23.4]
}
```

Frontend dùng `png_url` để lấy ảnh và dùng `bounds` để đặt ảnh lên bản đồ.

### Boundary

```http
GET /api/flood/boundary
```

Response là file GeoJSON của Việt Nam.

Nếu `vietnam.geojson` chưa tồn tại, backend tạo nó từ shapefile trước khi trả response.

### Refresh

```http
POST /api/flood/refresh
```

Flow:

1. Đọc token trong `data/.token`.
2. Gọi NASA để tải raster mới.
3. Ghi raster vào `data/vietnam_flood.tif`.
4. Xóa cache cũ.
5. Cắt và xử lý raster mới.
6. Tạo metrics mới.
7. Tạo overlay PNG mới.
8. Trả kết quả cho frontend.

Response mẫu:

```json
{
  "status": "refreshed",
  "flood_pixels": 12345,
  "flooded_km2": 771.56,
  "bounds": [102.1, 8.4, 109.5, 23.4]
}
```

### Inspect một điểm

Frontend gửi latitude và longitude:

```http
GET /api/flood/inspect?lat=21.0285&lon=105.8542
```

Flow:

1. Load flood mask.
2. Đọc bounds của mask.
3. Kiểm tra điểm có nằm trong bounds không.
4. Chuyển latitude/longitude thành row/column của array.
5. Đọc giá trị flood mask tại pixel đó.
6. Trả về `flooded: true` hoặc `flooded: false`.

Response khi điểm nằm trong vùng dữ liệu:

```json
{
  "inside": true,
  "flooded": false,
  "lat": 21.0285,
  "lon": 105.8542
}
```

Response khi điểm nằm ngoài vùng dữ liệu:

```json
{
  "inside": false,
  "flooded": null,
  "lat": 0,
  "lon": 0
}
```

## 8. Vai trò của từng file

| File | Vai trò |
| --- | --- |
| `app/config.py` | Cấu hình NASA tile, đường dẫn file và hằng số flood |
| `app/models.py` | Định nghĩa format response bằng Pydantic |
| `app/main.py` | Tạo FastAPI app, CORS, static files và đăng ký routes |
| `app/routes/health.py` | Health endpoint |
| `app/routes/flood.py` | Các API metrics, overlay, boundary, refresh và inspect |
| `app/core/downloader.py` | Tải raster từ NASA |
| `app/core/clipper.py` | Đọc boundary, crop raster và tạo flood mask |
| `app/core/renderer.py` | Render flood mask thành PNG trong suốt |
| `app/core/cache.py` | Tính metrics, đọc/ghi/xóa cache |
| `test_pipeline.py` | Smoke test cho pipeline local |

## 9. Chạy smoke test

Sau khi đã chuẩn bị boundary và raster:

```bash
cd backend/disaster-tracker-backend
uv run python test_pipeline.py
```

Script sẽ gọi pipeline cache và in ra:

```text
Metrics: ...
Bounds: ...
Overlay: ...
```

Smoke test này kiểm tra nhanh việc crop, tính metrics, render PNG và ghi cache.

## 10. Các assumption quan trọng

### CRS

Hàm `inspect()` giả định tọa độ input `lat/lon` và bounds của raster dùng cùng CRS địa lý.

Nếu raster dùng CRS dạng projection với đơn vị mét, việc kiểm tra điểm có thể sai. Cần xác nhận CRS của dataset NASA trước khi dùng cho số liệu thực tế.

### Cache freshness

Cache hiện chỉ kiểm tra file có tồn tại hay không. Nó chưa kiểm tra cache có thuộc raster mới nhất hay không.

Vì vậy refresh phải gọi `cache.invalidate()` trước khi build lại output.

### Diện tích pixel

`PIXEL_KM2` đang là hằng số cố định. Nếu độ phân giải raster thay đổi, diện tích tính ra cũng cần được cập nhật.

### Dữ liệu local

Các file sau chỉ nên tồn tại ở máy local:

```text
data/.token
data/vietnam_flood.tif
data/vietnam_boundary/vietnam.geojson
cache/*
```

Không commit token hoặc dữ liệu runtime lên Git.
