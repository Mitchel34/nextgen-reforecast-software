"""Public adapter checks need neither network access nor optional GIS decoders."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("public_fixture_forcing", Path(__file__).resolve().parents[1] / "scripts/public_fixture/prepare_forcing.py")
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)


class PublicForcingTests(unittest.TestCase):
    def test_ancestor_symlink_and_dotdot_escape_refused(self):
        tempbase=Path(__file__).resolve().parents[1]/'.local/tmp'
        tempbase.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tempbase) as directory:
            root=Path(directory)/'approved';root.mkdir()
            outside=Path(directory)/'outside';outside.mkdir()
            (root/'link').symlink_to(outside,target_is_directory=True)
            for path in [root/'link'/'payload.csv',root/'..'/'outside'/'payload.csv']:
                with self.subTest(path=path), self.assertRaises(recipe.PreparationError):
                    recipe.safe_path(path,root)
            self.assertEqual(recipe.safe_path(root/'fresh'/'payload.csv',root),root/'fresh'/'payload.csv')

    def test_year_specific_scale_is_applied(self):
        old={'_FillValue':-999,'scale_factor':.1,'add_offset':0}
        new={'_FillValue':-888,'scale_factor':2.,'add_offset':100}
        self.assertEqual(recipe.decode_source_value(10,old),1.)
        self.assertEqual(recipe.decode_source_value(10,new),120.)
        with self.assertRaises(recipe.PreparationError):recipe.decode_source_value(-888,new)

    def test_aorc_source_units_dims_codec_and_time_checked(self):
        array={'dtype':'<i2','chunks':[144,128,256],'shape':[8760,4201,8401],'order':'C','zarr_format':2,'filters':None,'compressor':{'checksum':False,'id':'zstd','level':3}}
        attrs={'units':'kg/m^2','aorc_version':'v1.1','_ARRAY_DIMENSIONS':['time','latitude','longitude'],'crs':'EPSG:4326'}
        meta={'APCP_surface/.zarray':array,'APCP_surface/.zattrs':attrs,'time/.zattrs':{'units':'seconds since 1970-01-01','calendar':'proleptic_gregorian','_ARRAY_DIMENSIONS':['time']},'time/.zarray':{'dtype':'<f8','chunks':[144]}}
        for coordinate,size,chunk,unit in [('latitude',4201,128,'degrees_north'),('longitude',8401,256,'degrees_east')]:
            meta[coordinate+'/.zarray']={'dtype':'<f8','shape':[size],'chunks':[chunk],'order':'C','compressor':{'checksum':False,'id':'zstd','level':3}}
            meta[coordinate+'/.zattrs']={'units':unit,'_ARRAY_DIMENSIONS':[coordinate]}
        recipe.validate_aorc_metadata(meta,'APCP_surface')
        for where,key,bad in [('APCP_surface/.zattrs','units','mm/s'),('APCP_surface/.zattrs','_ARRAY_DIMENSIONS',['latitude','longitude','time']),('APCP_surface/.zarray','order','F'),('APCP_surface/.zarray','compressor',{'id':'gzip'}),('time/.zattrs','units','hours since 1970-01-01')]:
            altered=json.loads(json.dumps(meta));altered[where][key]=bad
            with self.subTest(where=where,key=key),self.assertRaises(recipe.PreparationError):recipe.validate_aorc_metadata(altered,'APCP_surface')

    def test_actual_nwm_projection_and_coordinates_checked(self):
        attrs={'grid_mapping_name':'lambert_conformal_conic','standard_parallel':[30.,60.],'longitude_of_central_meridian':-97.,'latitude_of_projection_origin':40.,'false_easting':0.,'false_northing':0.,'earth_radius':6370000.,'semi_major_axis':6370000.,'inverse_flattening':0.}
        x=[-2303499.25+1000*i for i in range(4608)];y=[-1919500.375+1000*i for i in range(3840)]
        time={'units':'minutes since 1970-01-01 00:00:00 UTC','standard_name':'time'}
        ref={**time,'standard_name':'forecast_reference_time'}
        recipe.validate_nwm_grid(attrs,x,y,time,ref)
        with self.assertRaises(recipe.PreparationError):recipe.validate_nwm_grid({**attrs,'earth_radius':6378137.},x,y,time,ref)
        with self.assertRaises(recipe.PreparationError):recipe.validate_nwm_grid(attrs,[x[0]+.01]+x[1:],y,time,ref)
        with self.assertRaises(recipe.PreparationError):recipe.validate_nwm_grid(attrs,x,y,{**time,'units':'seconds since 1970-01-01'},ref)

    def test_raw_issue_and_valid_attributes_are_independent(self):
        issue = recipe.parse_hour("2022-01-01T23:00:00Z")
        attrs = {"model_initialization_time": "2022-01-01_23:00:00", "model_output_valid_time": "2022-01-02_17:00:00", "NWM_version_number": "v2.1", "model_configuration": "short_range", "model_output_type": "forcing"}
        report = recipe.validate_forecast_clock(attrs, issue, 18)
        self.assertEqual(report["provider_time_utc"], "2022-01-02T16:00:00Z")
        self.assertEqual(report["valid_time_utc"], "2022-01-02T17:00:00Z")
        for key, bad in [("model_initialization_time", "2022-01-02_00:00:00"), ("model_output_valid_time", "2022-01-02_16:00:00"), ("NWM_version_number", "v3.0"), ("model_configuration", "analysis_assim"), ("model_output_type", "land")]:
            with self.subTest(key=key), self.assertRaises(recipe.PreparationError):
                recipe.validate_forecast_clock({**attrs, key: bad}, issue, 18)

    def test_no_zero_lead_or_boolean_lead(self):
        for lead in [0, 19, True, 1.0]:
            with self.subTest(lead=lead), self.assertRaises(recipe.PreparationError):
                recipe.validate_forecast_clock({}, recipe.parse_hour("2022-01-01T23:00:00Z"), lead)

    def test_canonical_hours_only(self):
        for bad in ["2022-01-01T00:30:00Z", "2022-01-01T00:00:00+00:00", "2022-1-1T00:00:00Z"]:
            with self.subTest(bad=bad), self.assertRaises(recipe.PreparationError):
                recipe.parse_hour(bad)

    def test_weighted_decode_masks_before_scaling(self):
        self.assertAlmostEqual(recipe.weighted_value([100, 300], [.25, .75], -999, .01, 100), 102.5)
        with self.assertRaises(recipe.PreparationError):
            recipe.weighted_value([100, -999], [.25, .75], -999, .01, 100)

    def test_missing_cells_cannot_renormalize(self):
        for values, weights in [([1], [.9]), ([1, 2], [1, 0]), ([1, float("nan")], [.5, .5]), ([], []), ([1, 2], [.5])]:
            with self.subTest(values=values, weights=weights), self.assertRaises(recipe.PreparationError):
                recipe.weighted_value(values, weights, -999)

    def test_precipitation_treatments_are_separate(self):
        self.assertAlmostEqual(recipe.provider_precipitation(3.6, "AORC_APCP_kg_m-2_hour_end"), .001)
        self.assertEqual(recipe.provider_precipitation(.001, "NWM_RAINRATE_mm_s-1"), .001)
        for val, source in [(-1, "NWM_RAINRATE_mm_s-1"), (float("inf"), "AORC_APCP_kg_m-2_hour_end"), (1, "unknown")]:
            with self.subTest(val=val, source=source), self.assertRaises(recipe.PreparationError):
                recipe.provider_precipitation(val, source)

    def test_generation_and_byte_interval_are_bound(self):
        headers = {"ETag": '"abc"', "x-goog-generation": "123", "Content-Length": "4", "Content-Range": "bytes 20-23/100"}
        recipe.check_response(206, headers, 4, '"abc"', "123", (20, 23), 100)
        for status, altered in [(200, headers), (206, {**headers, "ETag": '"def"'}), (206, {**headers, "x-goog-generation": "124"}), (206, {**headers, "Content-Range": "bytes 21-24/100"}), (206, {**headers, "Content-Length": "100"})]:
            with self.subTest(status=status, altered=altered), self.assertRaises(recipe.PreparationError):
                recipe.check_response(status, altered, 4, '"abc"', "123", (20, 23), 100)


if __name__ == "__main__":
    unittest.main()
