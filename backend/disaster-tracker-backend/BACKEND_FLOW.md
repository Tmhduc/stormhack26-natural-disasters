# Luồng Backend

Tài liệu này mô tả luồng thực tế của backend theo code hiện tại.

## 1. Tổng quan hệ thống

```text
FastAPI khởi động
      |
      v
Poller LANCE chạy nền ----------------------+
      |                                      |
      v                                      |
Tìm ngày có đủ các tile cần thiết            |
      |                                      |
      v                                      |
Tải các tile mới hoặc được xử lý lại         |
      |                                      |
      v                                      |
Ghép thành data/vietnam_flood.tif             |
      |                                      |
      v                                      |
Cắt theo boundary Việt Nam                  |
      |                                      |
      v                                      |
Tạo flood mask (1 = ngập, 0 = còn lại)      |
      |                                      |
      +--> metrics.json                      |
      +--> bounds.json                       |
      +--> flood_overlay.png                 |
                                             |
API đọc state và cache <--------------------+
```

Backend dùng NASA LANCE và sản phẩm MODIS Near-Real-Time Global Flood
Product. Pipeline không tải một file cố định duy nhất. Nó tìm toàn bộ tile
cắt qua Việt Nam, chỉ chọn một ngày có đủ tile, ghép các tile thành mosaic rồi
mới cắt theo boundary Việt Nam.

## 2. Cấu hình và dữ liệu đầu vào

[`app/config.py`](app/config.py) đọc file `.env` trong thư mục backend.

Các cấu hình chính:

- `NASA_TOKEN`: bearer token dùng khi gọi API hoặc archive LANCE.
- Token phải được đặt trong biến môi trường hoặc file `.env`; backend không đọc
      token từ thư mục `data/`.
- `LANCE_PRODUCT`: mặc định là `MCDWD_L3_F2_NRT`.
- `LANCE_TILES`: danh sách tile cho phép, phân cách bằng dấu phẩy. Nếu để
  rỗng, backend tự tính các tile giao với boundary Việt Nam.
- `LANCE_LOOKBACK_DAYS`: số ngày lùi lại khi tìm một ngày có đủ tile.
- `LANCE_POLL_MINUTES`: khoảng cách giữa hai lần poll. Đặt `0` để tắt poller.

Boundary nguồn:

```text
data/vietnam_boundary/vnm_admin0.shp
```

Các file được tạo hoặc tải về:

```text
data/raw/YYYYDOY/<tile>.tif       tile nguồn tải từ LANCE
data/vietnam_flood.tif             mosaic các tile đã ghép
data/pipeline_state.json           trạng thái và lỗi của pipeline
cache/flood_overlay.png            ảnh overlay trong suốt
cache/metrics.json                 số liệu diện tích và số pixel
cache/bounds.json                  bounds WGS84 của overlay
cache/manifest.json                fingerprint của dữ liệu tạo cache
```

Các file trong danh sách trên là artifact runtime, không phải tất cả đều có
sẵn ngay sau khi clone repository. Chúng chỉ xuất hiện sau khi pipeline chạy
thành công ít nhất một lần. Lệnh chạy thủ công là:

```bash
uv run python -m app.core.pipeline --force
```

Các hằng số cũ `TILE_ID`, `YEAR`, `DOY` và `TILE_URL` vẫn còn trong
configuration để tương thích ngược, nhưng không được pipeline hiện tại dùng.

## 3. Metadata sản phẩm MCDWD đã xác nhận

Raster MCDWD có trong repository chứa metadata sau:

- Một band duy nhất.
- Kiểu dữ liệu `uint8`.
- Lưới địa lý 250 m.
- Giá trị `255`: dữ liệu không đủ, dùng làm nodata.
- Giá trị `0`: không có nước.
- Giá trị `1`: nước chuẩn theo reference water.
- Giá trị `2`: vùng ngập lặp lại theo mùa.
- Giá trị `3`: vùng ngập bất thường.

Backend hiện coi class `3` là vùng ngập để tạo binary flood mask.

Lưu ý: raster mẫu được commit trong repository là tile `h28v07`, chỉ phủ vùng
`100–110E, 10–20N`. Boundary Việt Nam thực tế kéo dài khoảng `102–117E` và
`7–23N`, nên raster mẫu này không đủ để đại diện cho toàn bộ Việt Nam. Phải
chạy pipeline nhiều tile để tạo dữ liệu hoàn chỉnh.

## 4. Khởi động ứng dụng

[`app/main.py`](app/main.py) thực hiện các bước:

1. Tạo ứng dụng FastAPI.
2. Bật CORS cho các cổng frontend local.
3. Tạo thư mục `cache/` và mount tại `/static`.
4. Đăng ký health router và flood router.
5. Khởi chạy `pipeline.poll_forever()` trong lifespan nếu poller được bật.

Poller chạy ngay một lần khi ứng dụng khởi động, sau đó đợi số phút đã cấu
hình rồi chạy lại. Lỗi pipeline được ghi log và thử lại ở chu kỳ sau, không làm
server dừng. Khi server shutdown, task poller bị hủy.

## 5. Luồng pipeline refresh

Luồng chính nằm trong [`app/core/pipeline.py`](app/core/pipeline.py). Một
`threading.Lock` ngăn poller và request refresh chạy đồng thời trong cùng
process.

### 5.1. Tìm tile cần tải

Pipeline dùng `LANCE_TILES` nếu cấu hình có giá trị. Nếu không, hàm
`clipper.boundary_tiles()` đọc boundary WGS84 và xác định các tile MCDWD lưới
10 độ giao với Việt Nam.

Ví dụ, Việt Nam có thể cần nhiều tile theo cả chiều kinh độ và vĩ độ; không
nên giả định chỉ có `h28v07`.

### 5.2. Tìm ngày có đủ dữ liệu

Nếu request không chỉ định `day`, hàm `downloader.find_latest()` kiểm tra
ngày UTC hiện tại rồi lùi dần trong `LANCE_LOOKBACK_DAYS` ngày.

Một ngày chỉ được chọn khi tất cả tile cần thiết đều xuất hiện và có trạng
thái `Online` trên API LANCE. Nếu thiếu một tile, ngày đó bị bỏ qua. Nếu không
có ngày nào đầy đủ, pipeline ném `LanceError`.

Điều này tránh việc ghép một mosaic chỉ có một phần tile của ngày hiện tại,
vì dữ liệu near-real-time thường được công bố dần theo các lượt vệ tinh bay
qua.

### 5.3. Tải và kiểm tra tile

Mỗi tile được lưu ở:

```text
data/raw/YYYYDOY/<filename>.tif
```

Downloader dùng HTTP session có retry cho một số lỗi tạm thời. Nếu có
`NASA_TOKEN`, request được gửi kèm:

```text
Authorization: Bearer <NASA_TOKEN>
```

File mới luôn được ghi vào file `.part`. Sau khi tải xong, backend:

1. Đếm số byte thực nhận.
2. So sánh với kích thước LANCE công bố.
3. Mở file bằng Rasterio để phát hiện HTML, payload lỗi hoặc GeoTIFF hỏng.
4. Dùng `os.replace()` để đổi tên file `.part` thành file thật.
5. Gắn thời gian sửa file theo `mtime` của phiên bản upstream.

Nếu một bước kiểm tra thất bại, file `.part` bị xóa và file thật cũ không bị
thay thế.

Tile được xem là hiện hành khi path tồn tại, kích thước khớp và mtime khớp
metadata của LANCE. Khi đó downloader không tải lại tile.

### 5.4. Kiểm tra và ghép mosaic

[`app/core/mosaic.py`](app/core/mosaic.py) đọc tile đầu tiên để lấy CRS,
resolution, dtype, số band và nodata làm metadata tham chiếu.

Các tile còn lại phải có cùng:

- CRS.
- Resolution.
- Kiểu dữ liệu.
- Số lượng band.
- Giá trị nodata.

Nếu khác, pipeline dừng với lỗi rõ ràng thay vì để `rasterio.merge` âm thầm
kế thừa profile sai từ tile đầu tiên.

Bounds boundary đầu vào là WGS84. Backend chuyển bounds sang CRS của tile rồi
gọi `rasterio.merge.merge()` với `target_aligned_pixels=True` để giữ lưới
pixel gốc, không tự resample.

Mosaic được ghi vào:

```text
data/vietnam_flood.tif.part
```

Sau khi ghi xong mới dùng `os.replace()` để thay thế:

```text
data/vietnam_flood.tif
```

Các tile cũ không còn cần thiết sẽ được prune sau khi rebuild thành công.

### 5.5. State của pipeline

Pipeline lưu state nguyên tử tại:

```text
data/pipeline_state.json
```

State gồm product, ngày dữ liệu, danh sách tile, version của từng tile, thời
điểm kiểm tra, thời điểm xử lý, metrics, bounds và lỗi gần nhất.

Nếu product, ngày, version tile, mosaic và cache đều khớp state cũ, pipeline
chỉ cập nhật `checked_at` và trả về `updated: false`. Nếu khác hoặc chạy với
`force=true`, pipeline tải/ghép lại dữ liệu.

## 6. Cắt raster và tạo flood mask

[`app/core/clipper.py`](app/core/clipper.py) thực hiện:

1. Đọc mosaic bằng Rasterio.
2. Đọc boundary bằng GeoPandas.
3. Chuyển boundary sang CRS của raster.
4. Dùng `rasterio.mask.mask()` với `crop=True` và `all_touched=False`.
5. Lấy band đầu tiên.
6. Chuyển `data == FLOOD_VALUE` thành `1`, giá trị còn lại thành `0`.

Với sản phẩm hiện tại:

```text
FLOOD_VALUE = 3
```

Bounds của array sau khi crop ban đầu nằm trong CRS raster. Backend chuyển
bounds này ngược về EPSG:4326 trước khi lưu cache hoặc trả về API, để frontend
luôn nhận bounds dạng:

```text
[left, bottom, right, top]
```

## 7. Tính diện tích và tạo cache

[`app/core/cache.py`](app/core/cache.py) dùng cùng một flood mask để tạo:

- `metrics.json`: số pixel ngập và diện tích ngập.
- `flood_overlay.png`: ảnh PNG trong suốt do
  [`app/core/renderer.py`](app/core/renderer.py) tạo.
- `bounds.json`: bounds WGS84 của ảnh.
- `manifest.json`: thông tin xác định dữ liệu nguồn của cache.

Pixel địa lý có diện tích thay đổi theo vĩ độ. Vì vậy với raster geographic,
backend dùng `pyproj.Geod` để tính diện tích địa trắc theo từng hàng pixel.
`0.0625 km²` chỉ còn là giá trị fallback khi thiếu metadata địa lý hoặc raster
là CRS projected chưa có cách tính diện tích tương ứng.

`manifest.json` lưu kích thước file raster, mtime raster, flood class, pixel
area fallback và phiên bản cách tính metrics. Cache chỉ được xem là hợp lệ
khi cả bốn file tồn tại và manifest khớp raster hiện tại.

Nếu thiếu file hoặc manifest không khớp, request kế tiếp sẽ build lại cache.

## 8. Các endpoint HTTP

Các route nằm trong [`app/routes/flood.py`](app/routes/flood.py).

### `GET /api/health`

Trả về:

```json
{"status": "ok"}
```

Đây chỉ là liveness check, xác nhận FastAPI đang trả response. Endpoint này
không kiểm tra raster, boundary, NASA token hoặc cache đã sẵn sàng hay chưa.

### `GET /api/flood/metrics`

Build hoặc đọc cache, đọc pipeline state rồi trả về metrics, product, tile,
ngày dữ liệu, thời điểm xử lý và bounds WGS84.

Ví dụ:

```json
{
  "flood_pixels": 12345,
  "flooded_km2": 771.56,
  "bounds": [102.1, 8.4, 109.5, 23.4],
  "product": "MCDWD_L3_F2_NRT",
  "tiles": ["h28v07", "h29v07"],
  "date": "2026-10-03",
  "last_updated": "2026-10-03T12:30:00+00:00"
}
```

### `GET /api/flood/overlay`

Đảm bảo cache tồn tại rồi trả về URL PNG và bounds WGS84:

```json
{
  "png_url": "/static/flood_overlay.png",
  "bounds": [102.1, 8.4, 109.5, 23.4]
}
```

PNG không chứa metadata địa lý. Client phải dùng bounds để đặt ảnh lên bản đồ.

### `GET /api/flood/boundary`

Nếu `vietnam.geojson` chưa tồn tại, backend tạo nó từ shapefile rồi trả về
GeoJSON cho frontend.

### `POST /api/flood/refresh`

Chạy pipeline ngay lập tức.

- `day`: ngày UTC cụ thể, định dạng `YYYY-MM-DD`.
- `force=true`: rebuild kể cả khi state cho rằng dữ liệu chưa đổi.
- Lỗi LANCE trả HTTP 502.
- Lỗi khác của pipeline trả HTTP 500.

### `GET /api/flood/status`

Trả về pipeline state đã lưu và khoảng poll cấu hình.

### `GET /api/flood/inspect?lat=<latitude>&lon=<longitude>`

Endpoint này:

1. Load mask đã clip cùng transform và CRS thật.
2. Kiểm tra điểm WGS84 có nằm trong geometry Việt Nam hay không.
3. Chuyển điểm WGS84 sang CRS của raster.
4. Dùng transform thật để lấy row/column.
5. Đọc giá trị flood mask tại pixel đó.

Điểm ngoài Việt Nam hoặc ngoài array sẽ trả `inside: false`. Tọa độ người
dùng gửi lên vẫn được giữ nguyên trong response.

## 9. Database layer

[`db/db.py`](db/db.py) và [`db/schema.sql`](db/schema.sql) định nghĩa các
bảng events, bulletins và images.

Hiện tại database layer chưa được import hoặc khởi tạo trong FastAPI startup,
flood routes hay pipeline. `DATABASE_URL` được đọc trong config nhưng chưa
tham gia vào luồng xử lý flood hiện tại.

## 10. Kiểm thử và chạy local

Khởi động backend:

```bash
cd backend/disaster-tracker-backend
uv run uvicorn app.main:app --reload
```

Chạy regression test offline:

```bash
uv run python -m unittest test_backend.py
```

`test_pipeline.py` là smoke test thật. Nó có thể gọi mạng, tải tile LANCE,
tạo mosaic, rebuild cache và ghi state; vì vậy không nên dùng nó làm unit test
mặc định trong CI nếu chưa mock API và thư mục dữ liệu.

Regression test hiện tại kiểm tra:

- Downloader từ chối file bị thiếu byte.
- Mosaic từ chối các tile có metadata không tương thích.
