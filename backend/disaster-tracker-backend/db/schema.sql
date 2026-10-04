-- Disaster Watch schema for Tiger Data (Tiger Cloud) or any Postgres 14+.
--
-- Run it once in the Tiger console's SQL editor, or from a terminal:
--   psql "$DATABASE_URL" -f backend/db/schema.sql
-- The backend also runs it on every startup, so it is safe to re-run (it never drops data).

create table if not exists events (
  id          text primary key,
  type        text not null,
  level       text not null,
  lon         double precision not null,
  lat         double precision not null,
  updated_at  timestamptz not null,
  data        jsonb not null           -- the full normalized Event
);

create table if not exists bulletins (
  id          text primary key,
  event_id    text not null,
  kind        text not null,
  head        text not null,
  body        text not null,
  by          text not null,
  created_at  timestamptz not null default now()
);
create index if not exists bulletins_created_idx on bulletins (created_at desc);

-- Processed imagery. The image-processing job turns feed pixel data into images and
-- either inserts rows here directly or uploads through POST /api/images.
--
-- GeoTIFFs: put the .tif bytes in `original` (original_media_type 'image/tiff') and leave
-- `data` and the footprint null. The API notices the insert, reads the GeoTIFF's own
-- georeferencing, and fills in `data` (a browser-ready PNG in Web Mercator) and the footprint.
create table if not exists images (
  id           bigint generated always as identity primary key,
  event_id     text,                         -- events.id this image is about (optional)
  source       text not null,                -- where the pixels came from, e.g. 'NASA GIBS'
  product      text not null default '',     -- what the image shows, e.g. 'VIIRS true color'
  captured_at  timestamptz not null,         -- when the pixels were observed
  created_at   timestamptz not null default now(),
  west         double precision,             -- footprint in WGS84 degrees, used to
  south        double precision,             -- place the image on the map
  east         double precision,
  north        double precision,
  width        integer,
  height       integer,
  media_type   text not null default 'image/png',
  data         bytea,                        -- what browsers get (PNG/JPEG/WebP)
  meta         jsonb not null default '{}'::jsonb,
  original     bytea,                        -- untouched source file, e.g. the GeoTIFF
  original_media_type text,                  -- e.g. 'image/tiff'
  crs          text,                         -- CRS of the original raster, e.g. 'EPSG:32610'
  bands        integer,                      -- band count of the original raster
  source_file  text                          -- upstream file name, e.g. 'MCDWD_L3_F2_NRT.A2026275.h08v05.061.tif'
);
-- Upgrades a table created by an earlier version of this file; no-ops on a fresh one.
alter table images add column if not exists original bytea;            -- untouched source file, e.g. the GeoTIFF
alter table images add column if not exists original_media_type text;
alter table images add column if not exists crs text;                  -- CRS of the original raster
alter table images add column if not exists bands integer;
alter table images add column if not exists source_file text;
alter table images alter column data drop not null;
alter table images alter column west drop not null;
alter table images alter column south drop not null;
alter table images alter column east drop not null;
alter table images alter column north drop not null;
create index if not exists images_event_idx on images (event_id, captured_at desc);
create index if not exists images_captured_idx on images (captured_at desc);
create index if not exists images_pending_idx on images (id) where data is null;
-- One row per upstream file, so re-running a download never stores a tile twice.
-- (Rows without a file name are not affected: Postgres treats NULLs as distinct.)
create unique index if not exists images_source_file_key on images (source_file);

-- Tell the API about every new image, however it was inserted, so browsers update live.
create or replace function notify_new_image() returns trigger language plpgsql as $$
begin
  perform pg_notify('new_image', new.id::text);
  return new;
end $$;
drop trigger if exists images_notify on images;
create trigger images_notify after insert on images for each row execute function notify_new_image();

-- Spatial queries ("events within 200 km of a hospital") when PostGIS is available.
-- Tiger Cloud ships PostGIS. If this role can't create the
-- extension, run `create extension postgis;` once as the admin user.
do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'postgis') then
    create extension if not exists postgis;
    if not exists (select 1 from information_schema.columns where table_name = 'events' and column_name = 'geom') then
      alter table events add column geom geography(Point, 4326)
        generated always as (st_setsrid(st_makepoint(lon, lat), 4326)::geography) stored;
      create index events_geom_idx on events using gist (geom);
    end if;
    if not exists (select 1 from information_schema.columns where table_name = 'images' and column_name = 'footprint') then
      alter table images add column footprint geometry(Polygon, 4326)
        generated always as (st_makeenvelope(west, south, east, north, 4326)) stored;
      create index images_footprint_idx on images using gist (footprint);
    end if;
  end if;
exception when insufficient_privilege then
  raise notice 'PostGIS not enabled (insufficient privilege); the app works without it';
end $$;
