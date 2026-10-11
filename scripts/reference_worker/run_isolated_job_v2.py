"""Private bounded Docker orchestration; all model launches use frozen tools."""
from pathlib import Path
import argparse, hashlib, io, json, os, shutil, signal, subprocess, sys, tarfile, time

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / 'scripts/physical_reference_v2'))
import common as c
import execute_stage

def setup():
    env = os.environ.copy()
    env.update(c.load(REPO / '.local/runtime-closure-20261010/worker-environment.json'))
    docker = ['docker', '--host', 'unix://' + env['COLIMA_HOME'] + '/nrf/docker.sock']
    return env, docker

def command(docker, env, args, *, data=None, timeout=60, maximum=1024*1024):
    p = subprocess.run(docker + args, env=env, input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    if len(p.stdout) + len(p.stderr) > maximum:
        raise RuntimeError('utility output byte bound')
    if p.returncode:
        raise RuntimeError('Docker utility failed: ' + p.stderr.decode(errors='replace')[-3000:])
    return p.stdout

def payload(assembly, admission, case, frozen):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w') as archive:
        entries = []
        for row in admission['case_inputs'][case]:
            p = assembly / case / c.relative(row['path'])
            if c.binding(p) != {'bytes': row['bytes'], 'sha256': row['sha256']}:
                raise RuntimeError('input bytes changed before transfer')
            entries.append(('job/' + row['path'], p))
        entries += [('PROTOCOL.json', frozen / 'PROTOCOL.json'), ('ADMISSION.json', frozen / 'ADMISSION.json')]
        entries += [('tools/' + p.name, p) for p in sorted((REPO / 'scripts/physical_reference_v2').glob('*.py'))]
        for name, p in entries:
            raw = c.read(p, 16*1024*1024)
            info = tarfile.TarInfo(name); info.size = len(raw); info.mode = 0o400
            archive.addfile(info, io.BytesIO(raw))
    raw = result.getvalue()
    if len(raw) > 32*1024*1024:
        raise RuntimeError('transfer payload byte bound')
    return raw

def accounting(docker, env, name):
    script = 'import json,pathlib; r=pathlib.Path("/sys/fs/cgroup"); print(json.dumps({n:(r/n).read_text() for n in ["cpu.max","cpu.stat","memory.max","memory.peak","memory.events","pids.max","pids.peak"]}))'
    raw = command(docker, env, ['exec', name, '/ngen/.venv/bin/python', '-c', script], timeout=15)
    return json.loads(raw)

def quiesce(docker, env, name):
    script='import os,signal,json; own=os.getpid(); killed=[]; errors=[]\nfor n in os.listdir("/proc"):\n if n.isdigit() and int(n)>1 and int(n)!=own:\n  try: os.kill(int(n),signal.SIGKILL);killed.append(int(n))\n  except ProcessLookupError: pass\n  except Exception as e: errors.append([int(n),str(e)])\nprint(json.dumps({"killed_container_pids":killed,"errors":errors,"pid1_kept_alive":True}))'
    return json.loads(command(docker,env,['exec',name,'/ngen/.venv/bin/python','-c',script],timeout=15))

def capture_tree(docker,env,name,remote,destination,maximum_bytes):
    destination=Path(destination)
    parent,leaf=remote.rsplit('/',1)
    archive_path=destination.parent/('.transfer-'+destination.name+'.tar')
    with archive_path.open('xb') as output:
        p=subprocess.run(docker+['exec',name,'/bin/tar','-cf','-','-C',parent,leaf],
                         env=env,stdout=output,stderr=subprocess.PIPE,timeout=120)
    transfer=c.binding(archive_path,maximum_bytes+8*1024*1024)
    if p.returncode:
        raise RuntimeError('container archive export failed: '+p.stderr.decode(errors='replace')[-2000:])
    total=0;count=0;seen=set()
    with tarfile.open(archive_path,'r') as archive:
        for member in archive:
            rel=c.relative(member.name.rstrip('/'))
            if rel in seen or rel.split('/')[0]!=leaf or not (member.isfile() or member.isdir()):
                raise RuntimeError('unsafe duplicate/special archive member')
            seen.add(rel);count+=1;total+=member.size
            if count>8192 or total>maximum_bytes:
                raise RuntimeError('archive extraction file/byte bound')
            target=destination if rel==leaf else destination/rel[len(leaf)+1:]
            if member.isdir():target.mkdir(exist_ok=True,parents=True)
            else:
                target.parent.mkdir(exist_ok=True,parents=True)
                with target.open('xb') as output, archive.extractfile(member) as source:
                    shutil.copyfileobj(source,output,64*1024)
    archive_path.unlink()
    return transfer

def allocated(roots):
    seen=set();total=0
    for root in roots:
        for p in root.rglob('*'):
            s=p.lstat()
            if p.is_symlink() or not p.is_file() or (s.st_dev,s.st_ino) in seen:
                continue
            seen.add((s.st_dev,s.st_ino));total+=s.st_blocks*512
    return total

def storage_bounds():
    runtime=allocated([REPO/'.local/runtime-closure-20261010', REPO/'.local/runtime-qualification-20261010', Path('/Users/mitchelcarson/Work/.nrf-rt-20261010')])
    fixture=allocated([REPO/'.local/public-fixture-20261010'])
    output=allocated([ROOT/'attempts',ROOT/'references'])
    result={'runtime_allocated_bytes':runtime,'fixture_allocated_bytes':fixture,'generated_allocated_bytes':output,
            'host_free_bytes':shutil.disk_usage(REPO).free}
    if runtime>12*1024**3 or fixture>2*1024**3 or output>4*1024**3 or result['host_free_bytes']<8*1024**3:
        raise RuntimeError('declared storage bound crossed: '+json.dumps(result))
    return result

def run(case, attempt_token):
    env, docker = setup()
    frozen = ROOT / 'frozen'
    protocol = c.verify(c.load(frozen / 'PROTOCOL.json'), 'protocol_identity_sha256')
    admitted = c.verify(c.load(frozen / 'ADMISSION.json'), 'admission_identity_sha256')
    freeze=c.load(frozen/'FREEZE.json')
    external_sha = freeze['admission_file']['sha256']
    if c.binding(Path(__file__))!=freeze['host_orchestrator']:
        raise RuntimeError('host orchestration source differs from freeze')
    execute_stage.admission(frozen / 'PROTOCOL.json', frozen / 'ADMISSION.json', external_sha)
    declared_tools={row['path']:row for row in protocol['tools']}
    actual_tools={p.relative_to(REPO).as_posix() for p in (REPO/'scripts/physical_reference_v2').glob('*.py')}
    if set(declared_tools)!=actual_tools:
        raise RuntimeError('transferred reference tool axis differs from freeze')
    for path,row in declared_tools.items():
        if c.binding(REPO/path)!={k:row[k] for k in ['bytes','sha256']}:
            raise RuntimeError('reference tool bytes differ from freeze')
    storage_before=storage_bounds()
    assembly = REPO / '.local/public-fixture-20261010/native-admitted-v2'
    data = payload(assembly, admitted, case, frozen)
    attempt = ROOT / 'attempts' / (case + '-' + attempt_token); attempt.mkdir(parents=True, exist_ok=False)
    name = 'nrf-reference-v2-' + case.lower().replace('serial-', '') + '-' + attempt_token
    digest = 'sha256:' + admitted['image_manifest_sha256']
    args = ['create', '--name', name, '--pull', 'never', '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '256',
            '--memory', '8g', '--memory-swap', '8g', '--cpus', '2',
            '--tmpfs', '/tmp:rw,exec,size=64m', '--tmpfs', '/work:rw,noexec,size=128m',
            '--tmpfs', '/work/job/outputs:rw,noexec,size=1g',
            '--env', 'LD_LIBRARY_PATH=' + admitted['native_ld_library_path'],
            '--env', 'OMP_NUM_THREADS=1', '--env', 'OPENBLAS_NUM_THREADS=1', '--env', 'MKL_NUM_THREADS=1',
            '--env', 'NUMEXPR_NUM_THREADS=1', '--env', 'TZ=UTC', '--env', 'PYTHONDONTWRITEBYTECODE=1',
            '--entrypoint', '/bin/sleep', digest, 'infinity']
    created = False
    capture = {'case_id': case, 'protocol_identity_sha256': protocol['protocol_identity_sha256'],
               'admission_identity_sha256': admitted['admission_identity_sha256'], 'create_argv': args,
               'transfer_payload': {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
               'stages': [], 'status': 'setting_up','storage_before':storage_before}
    proc=None
    try:
        command(docker, env, args); created = True
        command(docker, env, ['start', name])
        inspection = json.loads(command(docker, env, ['inspect', name]))[0]
        hc = inspection['HostConfig']
        if (hc['NetworkMode'], hc['ReadonlyRootfs'], hc['Memory'], hc['NanoCpus'], hc['PidsLimit']) != ('none', True, 8*1024**3, 2*10**9, 256):
            raise RuntimeError('container configured limit mismatch')
        if hc['Binds'] or inspection['Config']['Image'] != digest or hc['MemorySwap'] != 8*1024**3:
            raise RuntimeError('container binding/image/swap mismatch')
        capture['container_inspection'] = inspection
        command(docker, env, ['exec', '-i', name, '/bin/tar', '-xf', '-', '-C', '/work'], data=data)
        runtime_tar = REPO / '.local/runtime-qualification-20261010/export-runtime.tar'
        if c.binding(runtime_tar) != admitted['runtime_transfer_payload']:
            raise RuntimeError('runtime transfer payload differs')
        command(docker, env, ['exec', '-i', name, '/bin/tar', '-xf', '-', '-C', '/tmp'], data=c.read(runtime_tar))
        command(docker, env, ['exec', name, '/bin/mkdir', '-p', '/work/job/outputs/ngen', '/work/job/outputs/troute'])
        capture['cgroup_before'] = accounting(docker, env, name)
        if {k:capture['cgroup_before'][k].strip() for k in ['cpu.max','memory.max','pids.max']}!={'cpu.max':'200000 100000','memory.max':'8589934592','pids.max':'256'}:
            raise RuntimeError('actual cgroup limits differ from freeze')
        begin = time.monotonic()
        for stage in ['native', 'routing']:
            remaining = 1800 - (time.monotonic() - begin)
            reservation = execute_stage.reserve(frozen/'PROTOCOL.json', frozen/'ADMISSION.json', external_sha,
                                                case, stage, ROOT/'ledger', case.replace('_','-') + '-' + stage + '-' + attempt_token, remaining)
            rp = ROOT / 'ledger' / ('PROCESS-%02d.json' % reservation['process_number'])
            reservation_tar=io.BytesIO()
            with tarfile.open(fileobj=reservation_tar,mode='w') as archive:
                raw=c.read(rp);info=tarfile.TarInfo(rp.name);info.size=len(raw);info.mode=0o400;archive.addfile(info,io.BytesIO(raw))
            command(docker,env,['exec','-i',name,'/bin/tar','-xf','-','-C','/work'],data=reservation_tar.getvalue())
            argv = ['exec', name, '/ngen/.venv/bin/python', '/work/tools/execute_stage.py', 'run',
                    '/work/PROTOCOL.json', '/work/ADMISSION.json', external_sha, '/work/'+rp.name,
                    '/work/job', '/work/receipts/' + stage]
            stop_reason = None
            with (attempt / (stage + '-wrapper.log')).open('xb') as log:
                proc = subprocess.Popen(docker + argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                stage_begin = time.monotonic()
                last_storage_check=stage_begin
                while proc.poll() is None:
                    if time.monotonic() - begin > 1810:
                        stop_reason = 'host_whole_job_deadline'
                    if shutil.disk_usage(REPO).free < 8*1024**3:
                        stop_reason = 'host_free_space_floor'
                    if time.monotonic()-last_storage_check>5:
                        try: storage_bounds()
                        except RuntimeError: stop_reason='allocated_storage_bound'
                        last_storage_check=time.monotonic()
                    if stop_reason:
                        capture['forced_quiescence']=quiesce(docker,env,name)
                        proc.wait(timeout=15); break
                    time.sleep(1)
                code = proc.wait()
            capture['stages'].append({'stage':stage,'process_number':reservation['process_number'],
                                      'docker_exec_exit_code':code,'host_elapsed_seconds':time.monotonic()-stage_begin,
                                      'stop_reason':stop_reason,'wrapper_log':c.binding(attempt/(stage+'-wrapper.log'))})
            capture['cgroup_after_' + stage] = accounting(docker, env, name)
            capture['stages'][-1]['receipt_transfer']=capture_tree(docker,env,name,'/work/receipts/'+stage,attempt/stage,128*1024*1024)
            print(json.dumps({'case':case,'stage':stage,'exit_code':code,'elapsed':capture['stages'][-1]['host_elapsed_seconds']}), flush=True)
            if code:
                capture['status'] = 'model_stage_failed'; break
        else:
            capture['status'] = 'both_stages_zero_exit'
            raw = command(docker, env, ['exec', name, '/ngen/.venv/bin/python', '/work/tools/normalize_routing.py',
                                       '/work/PROTOCOL.json',case,'/work/job/outputs','/work/normalized'],timeout=120)
            capture['normalizer_stdout'] = raw.decode()
            capture['normalizer_transfer']=capture_tree(docker,env,name,'/work/normalized',attempt/'normalized',128*1024*1024)
        capture['output_transfer']=capture_tree(docker,env,name,'/work/job/outputs',attempt/'outputs',1024*1024*1024)
        capture['whole_job_model_elapsed_seconds'] = time.monotonic()-begin
        capture['host_free_bytes_after'] = shutil.disk_usage(REPO).free
        capture['storage_after']=storage_bounds()
    except BaseException as error:
        capture['error'] = type(error).__name__ + ': ' + str(error)
        if created:
            try: capture['exception_quiescence']=quiesce(docker,env,name)
            except Exception as e: capture['exception_container_stop_observation']=str(e)
            if proc is not None and proc.poll() is None:
                try: proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            capture['failed_outputs_disposition']='partial_unverified_after_model_quiescence; container tmpfs remains mounted until capture'
            try: capture['failed_output_transfer']=capture_tree(docker,env,name,'/work/job/outputs',attempt/'failed-outputs',1024*1024*1024)
            except Exception as e: capture['failed_output_capture_error'] = str(e)
        raise
    finally:
        capture['cleanup']=[]
        if created:
            for action in [['stop','--time','5',name],['rm','--force',name]]:
                try:
                    command(docker,env,action,timeout=30)
                    capture['cleanup'].append({'action':action[0],'status':'completed'})
                except Exception as e: capture['cleanup'].append({'action':action[0],'error':str(e)})
        c.write_new(attempt/'HOST_EXECUTION.json', c.seal(capture,'host_execution_identity_sha256'))
    return capture

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case');parser.add_argument('--attempt',default='a1');args=parser.parse_args()
    if args.attempt not in ['a1','a2','a3']:raise SystemExit('bounded attempt token required')
    result=run(args.case,args.attempt);print(json.dumps({'case':args.case,'status':result['status']}))
    if result['status']!='both_stages_zero_exit': raise SystemExit(1)
