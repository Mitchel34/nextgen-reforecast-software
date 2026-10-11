
import ctypes as c,json,pathlib,hashlib,math
p=pathlib.Path('/usr/lib64/libudunits2.so.0').resolve();lib=c.CDLL(str(p));ptr=c.c_void_p
lib.ut_read_xml.argtypes=[c.c_char_p];lib.ut_read_xml.restype=ptr
lib.ut_parse.argtypes=[ptr,c.c_char_p,c.c_int];lib.ut_parse.restype=ptr
lib.ut_get_converter.argtypes=[ptr,ptr];lib.ut_get_converter.restype=ptr
lib.cv_convert_double.argtypes=[ptr,c.c_double];lib.cv_convert_double.restype=c.c_double
lib.ut_get_path_xml.argtypes=[c.c_char_p,c.POINTER(c.c_int)];lib.ut_get_path_xml.restype=c.c_char_p
lib.ut_free.argtypes=[ptr];lib.ut_free_system.argtypes=[ptr];lib.cv_free.argtypes=[ptr]
status=c.c_int();xml=pathlib.Path(lib.ut_get_path_xml(None,c.byref(status)).decode());system=lib.ut_read_xml(None);assert system
results=[]
for source,target in [('m/s','mm h-1'),('mm h-1','m/s'),('m/s','m/s')]:
 a=lib.ut_parse(system,source.encode(),0);b=lib.ut_parse(system,target.encode(),0);assert a and b
 converter=lib.ut_get_converter(a,b);assert converter
 vals=[lib.cv_convert_double(converter,x) for x in [0.0,1.0,1e-6]]
 results.append({'source':source,'target':target,'inputs':[0.0,1.0,1e-6],'outputs':vals})
 lib.cv_free(converter);lib.ut_free(a);lib.ut_free(b)
lib.ut_free_system(system)
assert results[0]['outputs'][0]==0.0
assert math.isclose(results[0]['outputs'][1],3600000.0,rel_tol=1e-15)
assert math.isclose(results[0]['outputs'][2],3.6,rel_tol=1e-15)
print(json.dumps({'schema_version':'udunits-inert-numeric-check/1.0','image_manifest_sha256':'2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff','library':{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'default_xml':str(xml),'database_files':[{'path':str(x),'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in sorted(xml.parent.glob('*.xml'))],'conversions':results,'model_functions_called':False,'model_process_invocations':0}))
