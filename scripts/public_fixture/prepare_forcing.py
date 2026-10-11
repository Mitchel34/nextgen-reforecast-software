"""Prepare a separate Watauga development fixture from public AORC/NWM data.

Optional preparation dependencies: numpy, h5py, pyproj, shapely, zstandard.
This recipe does not run a model or admit physical/scientific qualification.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC = dt.timezone.utc
HOUR = dt.timedelta(hours=1)
AORC_ROOT = "https://noaa-nws-aorc-v1-1-1km.s3.amazonaws.com/"
NWM_ROOT = "https://storage.googleapis.com/national-water-model/"
AORC_VARS = ("APCP_surface", "TMP_2maboveground", "SPFH_2maboveground", "UGRD_10maboveground", "VGRD_10maboveground", "PRES_surface", "DSWRF_surface", "DLWRF_surface")
NWM_VARS = ("RAINRATE", "T2D", "Q2D", "U2D", "V2D", "PSFC", "SWDOWN", "LWDOWN")
OUTPUT_VARS = ("precip_rate",) + AORC_VARS[1:]
NWM_CRS = "+proj=lcc +units=m +a=6370000 +b=6370000 +lat_1=30 +lat_2=60 +lat_0=40 +lon_0=-97 +x_0=0 +y_0=0 +no_defs"


class PreparationError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def stamp(value):
    return value.strftime("%Y-%m-%dT%H:00:00Z")


def parse_hour(value):
    try:
        result = dt.datetime.strptime(value, "%Y-%m-%dT%H:00:00Z").replace(tzinfo=UTC)
    except ValueError as exc:
        raise PreparationError("Expected a canonical UTC integer hour") from exc
    if stamp(result) != value:
        raise PreparationError("Noncanonical hour")
    return result


def validate_forecast_clock(attrs, issue, lead):
    if type(lead) is not int or not 1 <= lead <= 18:
        raise PreparationError("Unsupported forecast lead")
    wanted = {
        "model_initialization_time": issue.strftime("%Y-%m-%d_%H:00:00"),
        "model_output_valid_time": (issue + lead * HOUR).strftime("%Y-%m-%d_%H:00:00"),
        "NWM_version_number": "v2.1",
        "model_configuration": "short_range",
        "model_output_type": "forcing",
    }
    for key, expected in wanted.items():
        if attrs.get(key) != expected:
            raise PreparationError(f"Forecast attribute disagreement: {key}")
    return {"issue_time_utc": stamp(issue), "valid_time_utc": stamp(issue + lead * HOUR), "provider_time_utc": stamp(issue + (lead - 1) * HOUR), "lead_hour": lead}


def weighted_value(values, weights, fill, scale=1.0, offset=0.0, nonnegative=False):
    if len(values) != len(weights) or not values:
        raise PreparationError("Values and spatial weights disagree")
    if any(not math.isfinite(float(w)) or w <= 0 for w in weights):
        raise PreparationError("Invalid spatial weights")
    if not math.isclose(math.fsum(weights), 1.0, abs_tol=1e-10):
        raise PreparationError("Spatial weights do not sum to one")
    decoded = []
    for raw in values:
        if raw == fill or not math.isfinite(float(raw)):
            raise PreparationError("Missing or nonfinite source cell; gap renormalization refused")
        val = float(raw) * scale + offset
        if not math.isfinite(val) or (nonnegative and val < 0):
            raise PreparationError("Invalid decoded forcing value")
        decoded.append(val)
    return math.fsum(w * val for w, val in zip(weights, decoded))


def provider_precipitation(value, source):
    if not math.isfinite(value) or value < 0:
        raise PreparationError("Invalid precipitation")
    if source == "AORC_APCP_kg_m-2_hour_end":
        return value / 3600.0
    if source == "NWM_RAINRATE_mm_s-1":
        return value
    raise PreparationError("Unqualified precipitation source/units")


def safe_path(path, root):
    path, root = Path(path).absolute(), Path(root).absolute()
    if not path.is_relative_to(root):
        raise PreparationError("Artifact is outside separate public-fixture staging")
    for component in [root, *reversed(list(path.parents)[:len(path.relative_to(root).parts)-1]), path]:
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_flags", 0) & getattr(stat, "UF_DATALESS", 0):
            raise PreparationError("Symlink/nonresident path component refused")
    if path.resolve(strict=False) != path:
        raise PreparationError("Resolved artifact path differs from declared staging path")
    return path


def bounded_file(path, bound):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > bound or getattr(before, "st_flags", 0) & getattr(stat, "UF_DATALESS", 0):
        raise PreparationError("Unsafe or oversized local artifact")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as handle:
        raw = handle.read(bound + 1)
        after = os.fstat(handle.fileno())
    if len(raw) != before.st_size or (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
        raise PreparationError("Local artifact changed during bounded read")
    return raw


def validate_aorc_metadata(meta, variable):
    array = meta[variable + "/.zarray"]
    attrs = meta[variable + "/.zattrs"]
    units = {"APCP_surface":"kg/m^2", "TMP_2maboveground":"K", "SPFH_2maboveground":"kg/kg", "UGRD_10maboveground":"m/s", "VGRD_10maboveground":"m/s", "PRES_surface":"Pa", "DSWRF_surface":"W/m^2", "DLWRF_surface":"W/m^2"}
    wanted = {"dtype":"<i2", "chunks":[144,128,256], "shape":[8760,4201,8401], "order":"C", "zarr_format":2, "filters":None, "compressor":{"checksum":False,"id":"zstd","level":3}}
    if any(array.get(k) != v for k,v in wanted.items()):
        raise PreparationError("AORC array encoding changed")
    if attrs.get("units") != units[variable] or attrs.get("aorc_version") != "v1.1" or attrs.get("_ARRAY_DIMENSIONS") != ["time","latitude","longitude"] or attrs.get("crs") != "EPSG:4326":
        raise PreparationError("AORC source units/dimensions/version changed")
    time_attrs=meta['time/.zattrs'];time_array=meta['time/.zarray']
    if time_attrs.get('units')!='seconds since 1970-01-01' or time_attrs.get('calendar')!='proleptic_gregorian' or time_attrs.get('_ARRAY_DIMENSIONS')!=['time'] or time_array.get('dtype')!='<f8' or time_array.get('chunks')!=[144]:
        raise PreparationError("AORC source time encoding changed")
    for coordinate, size, chunk, unit in [('latitude',4201,128,'degrees_north'),('longitude',8401,256,'degrees_east')]:
        a=meta[coordinate+'/.zarray'];b=meta[coordinate+'/.zattrs']
        if a.get('dtype')!='<f8' or a.get('shape')!=[size] or a.get('chunks')!=[chunk] or a.get('order')!='C' or a.get('compressor')!={'checksum':False,'id':'zstd','level':3} or b.get('units')!=unit or b.get('_ARRAY_DIMENSIONS')!=[coordinate]:
            raise PreparationError("AORC coordinate encoding changed")
    return attrs


def decode_source_value(raw, attrs):
    if raw == attrs['_FillValue']:
        raise PreparationError('Missing required source cell')
    result=float(raw)*attrs.get('scale_factor',1)+attrs.get('add_offset',0)
    if not math.isfinite(result):raise PreparationError('Nonfinite decoded source value')
    return result


def validate_nwm_grid(crs, x, y, time_attrs, reference_attrs):
    expected={"grid_mapping_name":"lambert_conformal_conic","standard_parallel":[30.0,60.0],"longitude_of_central_meridian":-97.0,"latitude_of_projection_origin":40.0,"false_easting":0.0,"false_northing":0.0,"earth_radius":6370000.0,"semi_major_axis":6370000.0,"inverse_flattening":0.0}
    if any(crs.get(k)!=v for k,v in expected.items()):
        raise PreparationError("Actual NWM projection differs from decoder CRS")
    if len(x)!=4608 or len(y)!=3840:
        raise PreparationError("Actual NWM grid size differs")
    if not math.isclose(float(x[0]),-2303499.25,abs_tol=1e-6,rel_tol=0) or not math.isclose(float(y[0]),-1919500.375,abs_tol=1e-6,rel_tol=0):
        raise PreparationError('Actual NWM coordinate origin differs')
    # Published vectors show <=0.125m rounding of nominal kilometre centers.
    # Retain their exact hashes and use their actual adjacent-center boundaries.
    if any(not math.isclose(float(val), -2303499.25+1000*i, abs_tol=.25, rel_tol=0) for i,val in enumerate(x)) or any(not math.isclose(float(val), -1919500.375+1000*i, abs_tol=.25, rel_tol=0) for i,val in enumerate(y)):
        raise PreparationError("Actual NWM coordinates differ from decoder")
    for attrs, name in [(time_attrs,'time'),(reference_attrs,'forecast_reference_time')]:
        if attrs.get('units')!='minutes since 1970-01-01 00:00:00 UTC' or attrs.get('standard_name')!=name:
            raise PreparationError("NWM time coordinate metadata changed")


def check_response(status, headers, expected_bytes, etag=None, generation=None, byte_range=None, total_bytes=None):
    expected_status = 206 if byte_range else 200
    if status != expected_status:
        raise PreparationError("Archive did not honor expected response/range")
    if etag is not None and headers.get("ETag") != etag:
        raise PreparationError("Source ETag changed")
    if generation is not None and headers.get("x-goog-generation") != generation:
        raise PreparationError("Source generation changed")
    if byte_range:
        start, stop = byte_range
        if headers.get("Content-Range") != f"bytes {start}-{stop}/{total_bytes}":
            raise PreparationError("Incorrect Content-Range")
    if headers.get("Content-Length") is not None and int(headers["Content-Length"]) != expected_bytes:
        raise PreparationError("Unexpected source response size")


class Archive:
    """Bounded anonymous downloader; every retained response has its own hash."""
    def __init__(self, root, *, max_bytes=768 * 1024**2, max_requests=2000):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=False)
        self.max_bytes = max_bytes
        self.max_requests = max_requests
        self.bytes = 0
        self.requests = 0
        self.records = []

    def get(self, url, *, expected_bytes=None, etag=None, generation=None, byte_range=None, total_bytes=None):
        if not url.startswith((AORC_ROOT, NWM_ROOT, "https://storage.googleapis.com/storage/v1/b/national-water-model/o?")):
            raise PreparationError("Unsupported public archive endpoint")
        bound = expected_bytes if expected_bytes is not None else 1024**2
        if bound > 16 * 1024**2 or bound < 1:
            raise PreparationError("Per-response byte bound exceeded")
        if self.requests >= self.max_requests or self.bytes + bound > self.max_bytes:
            raise PreparationError("Acquisition budget exceeded")
        self.requests += 1
        if shutil.disk_usage(self.root).free < 8*1024**3 + bound:
            raise PreparationError("Host free-space floor would be exceeded")
        headers = {}
        if etag: headers["If-Match"] = etag
        if byte_range: headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            actual_headers = dict(response.headers)
            if expected_bytes is not None:
                check_response(response.status, actual_headers, expected_bytes, etag, generation, byte_range, total_bytes)
            elif response.status != 200:
                raise PreparationError("Metadata response failed")
            data = response.read(bound + 1)
            if len(data) > bound or (expected_bytes is not None and len(data) != expected_bytes):
                raise PreparationError("Bounded source length disagreement")
        self.bytes += len(data)
        if self.bytes > self.max_bytes:
            raise PreparationError("Aggregate acquisition bound exceeded")
        name = digest(canonical({"url": url, "range": byte_range})) + ".bin"
        target = self.root / name
        if target.exists():
            if target.read_bytes() != data:
                raise PreparationError("Repeated source range changed")
        else:
            target.write_bytes(data)
        record = {"url": url, "generation": generation, "byte_range_inclusive": list(byte_range) if byte_range else None,
                  "response_size_bytes": len(data), "response_sha256": digest(data), "relative_cache_path": name,
                  "etag": actual_headers.get("ETag"), "last_modified": actual_headers.get("Last-Modified"),
                  "whole_object_sha256": digest(data) if not byte_range else None}
        self.records.append(record)
        return data

    def head(self, url):
        if not url.startswith((AORC_ROOT, NWM_ROOT)):
            raise PreparationError("Unsupported HEAD endpoint")
        if self.requests >= self.max_requests:
            raise PreparationError("Request budget exceeded")
        self.requests += 1
        with urlopen(Request(url, method="HEAD"), timeout=30) as response:
            if response.status != 200:
                raise PreparationError("Source object unavailable")
            return {"size_bytes": int(response.headers["Content-Length"]), "etag": response.headers.get("ETag"), "last_modified": response.headers.get("Last-Modified")}


class RangeFile(io.RawIOBase):
    def __init__(self, archive, item):
        self.archive = archive
        self.item = item
        self.url = NWM_ROOT + item["name"] + "?generation=" + item["generation"]
        self.pos = 0
        self.spans = []
        self.size = int(item["size"])
        import base64
        self.etag = '"' + base64.b64decode(item["md5Hash"]).hex() + '"'
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset if whence == 2 else -1
        if self.pos < 0: raise PreparationError("Invalid sparse seek")
        return self.pos
    def read(self, size=-1):
        if not 0 <= size <= 16 * 1024**2: raise PreparationError("Unbounded sparse read refused")
        end = min(self.pos + size, self.size)
        if end <= self.pos: return b""
        for begin, value in self.spans:
            if begin <= self.pos and begin + len(value) >= end:
                result = value[self.pos-begin:end-begin]; self.pos = end; return result
        if size < 16384:
            begin = self.pos // 65536 * 65536
            stop = min(max(begin + 65536, end), self.size) - 1
        else:
            begin, stop = self.pos, end - 1
        value = self.archive.get(self.url, expected_bytes=stop-begin+1, etag=self.etag, generation=self.item["generation"], byte_range=(begin, stop), total_bytes=self.size)
        self.spans.append((begin, value))
        result = value[self.pos-begin:end-begin]; self.pos = end
        return result
    def readinto(self, buffer):
        result = self.read(len(buffer)); buffer[:len(result)] = result; return len(result)


class ReplayArchive:
    """Recheck retained acquisition bytes without any HTTP request."""
    def __init__(self, original, destination, supplement=None):
        self.original=original
        receipt=json.loads(bounded_file(original/'PREPARATION.json',16*1024**2))
        saved=receipt.pop('preparation_identity_sha256')
        if digest(canonical(receipt))!=saved:raise PreparationError('Replay acquisition receipt changed')
        receipt['preparation_identity_sha256']=saved
        self.receipt=receipt
        self.root=destination;self.root.mkdir(parents=True,exist_ok=False)
        self.records=list(receipt['source_responses']);self.bytes=0;self.requests=0
        cache_roots={r['relative_cache_path']:original/'raw' for r in self.records}
        self.supplement_identity=None
        if supplement is not None:
            extra=json.loads(bounded_file(supplement/'SOURCE_COORDINATES.json',1024**2))
            self.supplement_identity=extra.pop('identity_sha256')
            if digest(canonical(extra))!=self.supplement_identity:raise PreparationError('Coordinate supplement changed')
            self.records+=extra['source_responses']
            cache_roots.update({r['relative_cache_path']:supplement/'raw' for r in extra['source_responses']})
        self.validated={}
        for record in self.records:
            name=record['relative_cache_path']
            if not isinstance(name,str) or '/'in name or not name.endswith('.bin'):raise PreparationError('Unsafe replay cache path')
            if name in self.validated:continue
            source=safe_path(cache_roots[name]/name,cache_roots[name].parent)
            raw=bounded_file(source,16*1024**2)
            if len(raw)!=record['response_size_bytes'] or digest(raw)!=record['response_sha256']:raise PreparationError('Retained source response changed')
            self.validated[name]=raw
            os.link(source,self.root/name)
    def get(self,url,*,expected_bytes=None,etag=None,generation=None,byte_range=None,total_bytes=None):
        for record in self.records:
            if record['url']!=url:continue
            saved=record['byte_range_inclusive']
            if byte_range is None and saved is not None:continue
            if byte_range is not None and (saved is None or saved[0]>byte_range[0] or saved[1]<byte_range[1]):continue
            if etag is not None and record['etag']!=etag:raise PreparationError('Replay source ETag differs')
            if generation is not None and record['generation']!=generation:raise PreparationError('Replay source generation differs')
            raw=self.validated[record['relative_cache_path']]
            if byte_range:
                raw=raw[byte_range[0]-saved[0]:byte_range[1]-saved[0]+1]
            if expected_bytes is not None and len(raw)!=expected_bytes:raise PreparationError('Replay range length differs')
            return raw
        raise PreparationError('Required range was not retained; offline replay cannot fetch')
    def head(self,url):
        for record in self.records:
            if record['url']==url and record['byte_range_inclusive'] is None:
                return {'size_bytes':record['response_size_bytes'],'etag':record['etag'],'last_modified':record['last_modified']}
        raise PreparationError('Required whole object not retained')


def gpkg_geometries(path, table, id_column, geometry_column, expected_ids):
    from shapely import from_wkb
    if any(not s.replace("_", "").isalnum() for s in (table, id_column, geometry_column)):
        raise PreparationError("Unsafe GeoPackage field name")
    before = path.stat()
    if path.is_symlink() or getattr(before, "st_flags", 0) & getattr(__import__("stat"), "UF_DATALESS", 0):
        raise PreparationError("Unsafe/nonresident public geometry")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        contents = connection.execute("SELECT srs_id FROM gpkg_contents WHERE table_name=?", (table,)).fetchone()
        if contents is None or contents[0] != 5070: raise PreparationError("Expected EPSG:5070 public domain")
        rows = connection.execute(f'SELECT "{id_column}", "{geometry_column}" FROM "{table}"').fetchall()
    finally:
        connection.close()
    result = {}
    envelope_bytes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    for identifier, blob in rows:
        if identifier not in expected_ids: continue
        if identifier in result or blob[:2] != b"GP": raise PreparationError("Duplicate/invalid catchment geometry")
        envelope = (blob[3] >> 1) & 7
        if envelope not in envelope_bytes: raise PreparationError("Unsupported GeoPackage envelope")
        geom = from_wkb(blob[8 + envelope_bytes[envelope]:])
        if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise PreparationError("Invalid public catchment polygon")
        result[identifier] = geom
    if set(result) != set(expected_ids): raise PreparationError("Geometry differs from independently sealed axis")
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise PreparationError("Public geometry changed during preparation")
    return result


def spatial_weights(geometries, x, y, crs):
    from pyproj import Transformer
    from shapely.geometry import Polygon
    from shapely.ops import transform
    import numpy as np
    to_grid = Transformer.from_crs(5070, crs, always_xy=True).transform
    to_area = Transformer.from_crs(crs, 5070, always_xy=True).transform
    dx, dy = float(x[1]-x[0]), float(y[1]-y[0])
    if dx <= 0 or dy <= 0: raise PreparationError("Grid coordinates must increase")
    xedges=np.r_[x[0]-dx/2,(x[:-1]+x[1:])/2,x[-1]+float(x[-1]-x[-2])/2]
    yedges=np.r_[y[0]-dy/2,(y[:-1]+y[1:])/2,y[-1]+float(y[-1]-y[-2])/2]
    result = {}
    for identifier, geom in sorted(geometries.items()):
        xmin, ymin, xmax, ymax = transform(to_grid, geom).bounds
        columns = np.where((xedges[1:] >= xmin) & (xedges[:-1] <= xmax))[0]
        rows = np.where((yedges[1:] >= ymin) & (yedges[:-1] <= ymax))[0]
        cells = []
        for row in rows:
            for col in columns:
                left, right = float(xedges[col]), float(xedges[col+1])
                bottom, top = float(yedges[row]), float(yedges[row+1])
                # Densify each transformed edge at quarter-cell positions.
                ring = [(left+(right-left)*i/4,bottom) for i in range(4)] + [(right,bottom+(top-bottom)*i/4) for i in range(4)] + [(right-(right-left)*i/4,top) for i in range(4)] + [(left,top-(top-bottom)*i/4) for i in range(4)]
                cell = transform(to_area, Polygon(ring))
                area = geom.intersection(cell).area
                if area > 0: cells.append({"row": int(row), "column": int(col), "intersection_area_m2": area})
        covered = math.fsum(c["intersection_area_m2"] for c in cells)
        if not cells or not math.isclose(covered, geom.area, rel_tol=1e-5, abs_tol=.01):
            raise PreparationError("Grid fails complete polygon coverage")
        for cell in cells: cell["weight"] = cell["intersection_area_m2"] / covered
        result[identifier] = {"polygon_area_m2": geom.area, "covered_area_m2": covered, "cells": cells}
    return result


def aorc_forcing(archive, geometries, origin, stop, output):
    import numpy as np
    import zstandard
    years = list(range(origin.year, stop.year + 1))
    metadata = {}
    grid_records = []
    decoder = zstandard.ZstdDecompressor()
    for year in years:
        raw = archive.get(f"{AORC_ROOT}{year}.zarr/.zmetadata")
        metadata[year] = json.loads(raw)["metadata"]
    meta = metadata[origin.year]
    # Coordinate chunks are small; retain exact published coordinate values.
    coords = {}
    for name in ("latitude", "longitude"):
        arrmeta = meta[name + "/.zarray"]
        values = []
        for index in range(math.ceil(arrmeta["shape"][0] / arrmeta["chunks"][0])):
            url = f"{AORC_ROOT}{origin.year}.zarr/{name}/{index}"
            head = archive.head(url)
            raw = archive.get(url, expected_bytes=head["size_bytes"], etag=head["etag"])
            values.extend(np.frombuffer(decoder.decompress(raw, max_output_size=65536), dtype=arrmeta["dtype"]).tolist())
        coords[name] = np.asarray(values[:arrmeta["shape"][0]])
        for year in years[1:]:
            values=[]
            for index in range(math.ceil(arrmeta['shape'][0]/arrmeta['chunks'][0])):
                url=f'{AORC_ROOT}{year}.zarr/{name}/{index}'
                head=archive.head(url);raw=archive.get(url,expected_bytes=head['size_bytes'],etag=head['etag'])
                values.extend(np.frombuffer(decoder.decompress(raw,max_output_size=65536),dtype=arrmeta['dtype']).tolist())
            if not np.array_equal(coords[name],np.asarray(values[:arrmeta['shape'][0]])):
                raise PreparationError('Actual cross-year AORC coordinate vectors differ')
    weights = spatial_weights(geometries, coords["longitude"], coords["latitude"], "EPSG:4326")
    (output / "aorc-spatial-weights.json").write_bytes(canonical(weights) + b"\n")
    hours = [origin + i*HOUR for i in range(int((stop-origin)/HOUR))]
    data = {cat: {stamp(hour): {} for hour in hours} for cat in geometries}
    times_cache = {}
    for variable in AORC_VARS:
        pending = {}
        for provider in hours:
            source = provider + HOUR if variable == "APCP_surface" else provider
            year = source.year
            hour_index = int((source - dt.datetime(year,1,1,tzinfo=UTC))/HOUR)
            arrmeta = metadata[year][variable + "/.zarray"]
            attrs = validate_aorc_metadata(metadata[year],variable)
            for cat, entry in weights.items():
                for cell in entry["cells"]:
                    key=(year,hour_index//144,cell["row"]//128,cell["column"]//256)
                    pending.setdefault(key, []).append((cat,provider,hour_index,cell))
        partial = {}
        for (year,tile_t,tile_y,tile_x), uses in sorted(pending.items()):
            time_key=(year,tile_t)
            if time_key not in times_cache:
                time_url=f"{AORC_ROOT}{year}.zarr/time/{tile_t}"
                h=archive.head(time_url);raw=archive.get(time_url,expected_bytes=h["size_bytes"],etag=h["etag"])
                times_cache[time_key]=np.frombuffer(decoder.decompress(raw,max_output_size=65536),dtype="<f8")
            url=f"{AORC_ROOT}{year}.zarr/{variable}/{tile_t}.{tile_y}.{tile_x}"
            head=archive.head(url);raw=archive.get(url,expected_bytes=head["size_bytes"],etag=head["etag"])
            cube=np.frombuffer(decoder.decompress(raw,max_output_size=144*128*256*2),dtype="<i2").reshape((144,128,256))
            attrs=metadata[year][variable+"/.zattrs"]
            for cat,provider,hour_index,cell in uses:
                source=provider+HOUR if variable=="APCP_surface" else provider
                if times_cache[time_key][hour_index%144] != source.timestamp():
                    raise PreparationError("AORC decoded time does not match requested source hour")
                value=cube[hour_index%144,cell["row"]%128,cell["column"]%256].item()
                decoded=decode_source_value(value,attrs)
                partial.setdefault((cat,stamp(provider)),[]).append((decoded,cell["weight"]))
        for (cat,hour), values in partial.items():
            data[cat][hour][variable]=weighted_value([v for v,w in values],[w for v,w in values],float('nan'),nonnegative=variable=="APCP_surface")
        print("AORC",variable,"complete",len(partial),"catchment-hours",flush=True)
    grid={"crs":"EPSG:4326","latitude_sha256":digest(coords["latitude"].tobytes()),"longitude_sha256":digest(coords["longitude"].tobytes()),"metadata_sha256":{str(y):digest(canonical(metadata[y])) for y in years},"weights_sha256":digest(canonical(weights))}
    return data,grid


def native(value):
    import numpy as np
    if isinstance(value,bytes): return value.decode()
    if isinstance(value,np.ndarray):
        return native(value.item()) if value.size==1 else value.tolist()
    if isinstance(value,np.generic): return value.item()
    return value


def nwm_forcing(archive, geometries, issues, output):
    import h5py
    import numpy as np
    objects=[]; data={}; grids=[]; weights=None; clock_records=[]
    for issue in issues:
        prefix=f"nwm.{issue:%Y%m%d}/forcing_short_range/nwm.t{issue:%H}z.short_range.forcing."
        query=urlencode({"prefix":prefix,"maxResults":"30","fields":"items(name,size,generation,md5Hash,crc32c,updated),nextPageToken"})
        listing=json.loads(archive.get("https://storage.googleapis.com/storage/v1/b/national-water-model/o?"+query))
        expected=[prefix+f"f{lead:03}.conus.nc" for lead in range(1,19)]
        if listing.get("nextPageToken") or [i["name"] for i in listing.get("items",[])] != expected:
            raise PreparationError("Forecast archive lacks exact 18-object issue coverage")
        data[stamp(issue)]={cat:{} for cat in geometries}
        for lead,item in enumerate(listing["items"],1):
            objects.append(item); source=RangeFile(archive,item)
            with h5py.File(source,"r") as dataset:
                attrs={key:native(val) for key,val in dataset.attrs.items()}
                clock=validate_forecast_clock(attrs,issue,lead)
                minutes=int(dataset['time'][0]); ref=int(dataset['reference_time'][0])
                if minutes*60!=(issue+lead*HOUR).timestamp() or ref*60!=issue.timestamp():
                    raise PreparationError("NWM coordinate and global clocks disagree")
                x=dataset['x'][...]; y=dataset['y'][...]
                grid={"x_sha256":digest(x.tobytes()),"y_sha256":digest(y.tobytes()),"crs_attrs":{k:native(v) for k,v in dataset['crs'].attrs.items()}}
                for name in ('x','y'):
                    coord_attrs={k:native(v) for k,v in dataset[name].attrs.items() if k not in ('REFERENCE_LIST',)}
                    if coord_attrs.get('units')!='m' or coord_attrs.get('standard_name')!=f'projection_{name}_coordinate' or coord_attrs.get('resolution')!=1000.:
                        raise PreparationError('NWM spatial coordinate metadata differs')
                    grid[name+'_attrs']=coord_attrs
                validate_nwm_grid(grid['crs_attrs'],x,y,{k:native(v) for k,v in dataset['time'].attrs.items()},{k:native(v) for k,v in dataset['reference_time'].attrs.items()})
                if grids and grid!=grids[0]: raise PreparationError("NWM grid changed within fixture")
                if weights is None:
                    weights=spatial_weights(geometries,x,y,NWM_CRS)
                    (output/'nwm-spatial-weights.json').write_bytes(canonical(weights)+b'\n')
                grids.append(grid)
                values={cat:{} for cat in geometries};var_attrs={};var_encoding={}
                for variable in NWM_VARS:
                    var=dataset[variable];a={k:native(v) for k,v in var.attrs.items() if k not in ('DIMENSION_LIST','REFERENCE_LIST')};var_attrs[variable]=a
                    expected_units={"RAINRATE":"mm s^-1","T2D":"K","Q2D":"kg kg-1","U2D":"m s-1","V2D":"m s-1","PSFC":"Pa","SWDOWN":"W m-2","LWDOWN":"W m-2"}[variable]
                    if a.get('units')!=expected_units:raise PreparationError("NWM source units changed")
                    dims=[list(dim.keys()) for dim in var.dims]
                    var_encoding[variable]={'shape':list(var.shape),'dtype':str(var.dtype),'chunks':list(var.chunks),'compression':var.compression,'compression_opts':var.compression_opts,'dimensions':dims}
                    if var.shape!=(1,3840,4608) or str(var.dtype)!=('float32' if variable=='RAINRATE' else 'int32') or dims!=[['time'],['y'],['x']] or var.compression!='gzip':
                        raise PreparationError('NWM source dimension/encoding differs')
                    if a.get('cell_methods')!=('time: mean' if variable=='RAINRATE' else 'time point' if variable=='SWDOWN' else 'time: point'):
                        raise PreparationError('NWM variable temporal treatment changed')
                    allcells=[cell for entry in weights.values() for cell in entry['cells']]
                    ar0,ar1=min(c['row'] for c in allcells),max(c['row'] for c in allcells)+1
                    ac0,ac1=min(c['column'] for c in allcells),max(c['column'] for c in allcells)+1
                    allpiece=var[0,ar0:ar1,ac0:ac1]
                    for cat,entry in weights.items():
                        cells=entry['cells']; rows=[c['row'] for c in cells];cols=[c['column'] for c in cells]
                        r0,r1,c0,c1=min(rows),max(rows)+1,min(cols),max(cols)+1
                        raw=[allpiece[c['row']-ar0,c['column']-ac0].item() for c in cells]
                        values[cat][variable]=weighted_value(raw,[c['weight'] for c in cells],a['_FillValue'],a.get('scale_factor',1),a.get('add_offset',0),variable=='RAINRATE')
                for cat in geometries:data[stamp(issue)][cat][clock['provider_time_utc']]=values[cat]
                clock_records.append({**clock,"object_key":item['name'],"generation":item['generation'],"source_attributes":attrs,"variable_attributes":var_attrs,"variable_encoding":var_encoding})
            print("NWM",stamp(issue),"lead",lead,"complete",flush=True)
    return data,{**grids[0],"weights_sha256":digest(canonical(weights))},objects,clock_records


def write_csv(path,rows,header):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as handle:
        writer=csv.writer(handle,lineterminator='\n');writer.writerow(header);writer.writerows(rows)
    raw=path.read_bytes()
    return {"path":str(path),"size_bytes":len(raw),"sha256":digest(raw)}


def main(argv=None):
    executed_recipe_sha256=digest(Path(__file__).read_bytes())
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--domain',type=Path,required=True);p.add_argument('--axis',type=Path,required=True)
    p.add_argument('--table',default='divides');p.add_argument('--id-column',default='divide_id');p.add_argument('--geometry-column',default='geom')
    p.add_argument('--origin',default='2021-12-01T00:00:00Z');p.add_argument('--stop',default='2022-01-02T18:00:00Z')
    p.add_argument('--issue',action='append',default=[]);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--max-download-bytes',type=int,default=700*1024**2)
    p.add_argument('--replay-from',type=Path,help='Revalidate retained source responses without network access')
    p.add_argument('--replay-coordinate-supplement',type=Path)
    args=p.parse_args(argv)
    args.domain=args.domain.absolute();args.axis=args.axis.absolute();args.out=args.out.absolute()
    checkout=Path(__file__).resolve().parents[2]
    local=(checkout/'.local/public-fixture-20261010').resolve()
    for path in (args.domain,args.axis,args.out):safe_path(path,local)
    if args.out.exists():raise PreparationError('Use a fresh output directory')
    if args.max_download_bytes>700*1024**2:raise PreparationError('Declared weather acquisition bound exceeded')
    domain_bytes=bounded_file(args.domain,16*1024**2)
    axis_bytes=bounded_file(args.axis,1024**2)
    axis=json.loads(axis_bytes);cats=axis['catchment_ids']
    geometry_binding=axis.get('geometry',{})
    if geometry_binding.get('sha256')!=digest(domain_bytes) or geometry_binding.get('bytes')!=len(domain_bytes):
        raise PreparationError('Supplied domain receipt does not bind selected GeoPackage')
    if not isinstance(cats,list) or len(set(cats))!=len(cats) or not 1<=len(cats)<=64:raise PreparationError('Invalid independently supplied domain axis')
    origin,stop=parse_hour(args.origin),parse_hour(args.stop)
    issues=[parse_hour(value) for value in (args.issue or ['2022-01-01T23:00:00Z','2022-01-02T00:00:00Z'])]
    if len(set(issues))!=len(issues) or issues!=sorted(issues):raise PreparationError('Issue axis must be unique and increasing')
    if stop<=origin or (stop-origin)/HOUR>1000 or len(issues)>2:raise PreparationError('Development fixture clocks exceed approved bounds')
    if min(issues)<origin or max(issues)+18*HOUR>stop:raise PreparationError('Issue/target clocks outside fixture history')
    args.out.mkdir(parents=True)
    geometries=gpkg_geometries(args.domain,args.table,args.id_column,args.geometry_column,cats)
    if bounded_file(args.domain,16*1024**2)!=domain_bytes or bounded_file(args.axis,1024**2)!=axis_bytes:
        raise PreparationError('Domain/axis changed after sealing geometry')
    if args.replay_from:
        args.replay_from=safe_path(args.replay_from.absolute(),local)
        supplement=safe_path(args.replay_coordinate_supplement.absolute(),local) if args.replay_coordinate_supplement else None
        archive=ReplayArchive(args.replay_from,args.out/'raw',supplement)
    else:
        archive=Archive(args.out/'raw',max_bytes=args.max_download_bytes)
    history,hgrid=aorc_forcing(archive,geometries,origin,stop,args.out)
    history_records=list(archive.records)
    forecast,fgrid,objects,clocks=nwm_forcing(archive,geometries,issues,args.out)
    if bounded_file(args.domain,16*1024**2)!=domain_bytes or bounded_file(args.axis,1024**2)!=axis_bytes:
        raise PreparationError('Domain/axis changed during forcing preparation')
    fields=['catchment_id','provider_time_utc','precip_source_time_utc','other_source_time_utc','issue_time_utc','lead_hour']
    rows=[];payloads=[]
    for cat in sorted(cats):
        provider=[]
        for time,weather in sorted(history[cat].items()):
            hour=parse_hour(time)
            rows.append([cat,time,stamp(hour+HOUR),time,'','']+[format(weather[v],'.17g') for v in AORC_VARS])
            native_time=hour.strftime('%Y-%m-%d %H:%M:%S')
            provider.append([native_time,format(provider_precipitation(weather['APCP_surface'],'AORC_APCP_kg_m-2_hour_end'),'.17g')]+[format(weather[v],'.17g') for v in AORC_VARS[1:]])
        payloads.append(write_csv(args.out/'provider/history'/f'{cat}.csv',provider,['time']+list(OUTPUT_VARS)))
    history_payload=write_csv(args.out/'decoded/history.csv',rows,fields+['APCP']+list(AORC_VARS[1:]));payloads.append(history_payload)
    forecast_payloads=[]
    for issue in issues:
        token=issue.strftime('%Y%m%dT%H00Z');rows=[]
        for cat in sorted(cats):
            provider=[]
            for lead,(time,weather) in enumerate(sorted(forecast[stamp(issue)][cat].items()),1):
                source=stamp(issue+lead*HOUR)
                rows.append([cat,time,source,source,stamp(issue),lead]+[format(weather[v],'.17g') for v in NWM_VARS])
                provider.append([parse_hour(time).strftime('%Y-%m-%d %H:%M:%S')]+[format(weather[v],'.17g') for v in NWM_VARS])
            payloads.append(write_csv(args.out/'provider/forecast'/token/f'{cat}.csv',provider,['time']+list(OUTPUT_VARS)))
        forecast_payloads.append(write_csv(args.out/'decoded'/f'forecast-{token}.csv',rows,fields+list(NWM_VARS)))
    payloads+=forecast_payloads
    # Reports use paths relative to this private preparation directory.
    for payload in payloads:payload['path']=str(Path(payload['path']).relative_to(args.out))
    report={'schema_version':'public-forcing-preparation/0.1','fixture_class':'prospective_development','fixture_id':'watauga-public-rebuild-v1','historical_benchmark_restored':False,
            'content_complete':True,'execution_ready':False,'physical_qualification':False,'source_issue_attributes_verified':True,'historical_operational_availability_verified':False,
            'domain_sha256':digest(domain_bytes),'axis_sha256':digest(axis_bytes),'catchment_ids':sorted(cats),'origin_time_utc':stamp(origin),'stop_time_utc_exclusive':stamp(stop),'issue_times_utc':[stamp(i) for i in issues],
            'history_catchment_hours':len(cats)*int((stop-origin)/HOUR),'forecast_catchment_hours':len(cats)*len(issues)*18,'history_grid':hgrid,'forecast_grid':fgrid,
            'spatial_method':'polygon intersection area in EPSG:5070; source cell edges densified at quarter-cell intervals; no missing-cell renormalization',
            'native_provider_time_encoding':'UTC rendered as %Y-%m-%d %H:%M:%S for pinned ngen CsvPerFeature parser; decoded source CSVs retain canonical UTC Z timestamps',
            'precipitation_treatment':{'history':'APCP end-labelled one-hour accumulated kg/m^2 divided by3600 exactly once','forecast':'RAINRATE mm/s equivalent to kg/m^2/s for liquid-water depth; no division'},
            'radiation_treatment':{'history':'same-label source values; physical interval interpretation unqualified','forecast':'source SWDOWN cell_methods time point; end-labelled provider sampling; physical suitability unqualified'},
            'qualification_blockers':['prospective fixture needs independent physical references','current AORC registry masking/regeneration notice unresolved for release','shortwave sampling physical interpretation not qualified','runtime/configuration/profile qualification separate','archive current generation is not proof of causal availability at issue'],
            'recipe_sha256':executed_recipe_sha256,'payloads':payloads,'source_objects':objects,'source_responses':archive.records,'source_clock_records':clocks,
            'downloaded_response_bytes':archive.bytes,'http_request_count':archive.requests,'history_response_count':len(history_records)}
    if args.replay_from:
        report['acquisition_preparation_identity_sha256']=archive.receipt['preparation_identity_sha256']
        report['acquisition_response_bytes']=archive.receipt['downloaded_response_bytes']
        report['offline_source_revalidation']=True
        report['cross_year_coordinate_supplement_identity_sha256']=archive.supplement_identity
    report['preparation_identity_sha256']=digest(canonical(report))
    (args.out/'PREPARATION.json').write_bytes(canonical(report)+b'\n')
    print(json.dumps({'content_complete':True,'downloaded_bytes':archive.bytes,'requests':archive.requests,'preparation_identity_sha256':report['preparation_identity_sha256']},indent=2))
    return report


if __name__=='__main__':
    main()
