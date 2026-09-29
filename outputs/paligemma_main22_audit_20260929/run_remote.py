"""Execute a supplied read-only audit through the existing SSH identity."""
import pathlib, subprocess, sys

base = pathlib.Path(__file__).resolve().parent
source = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
cmd = [r'C:\Windows\System32\OpenSSH\ssh.exe', '-i',
       str(pathlib.Path.home()/'.ssh/id_ed25519_bridge'), '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=15', 'ph_teacher3@10.68.162.201']
if len(sys.argv) > 3:
    cmd += ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', sys.argv[3]]
cmd += ['python3', '-u', '-']
with output.open('wb') as out, output.with_suffix('.stderr.txt').open('wb') as err:
    result = subprocess.run(cmd, input=source.read_bytes(), stdout=out, stderr=err, timeout=600)
print('exit_code=', result.returncode, 'output=', output, 'bytes=', output.stat().st_size, flush=True)
sys.exit(result.returncode)
