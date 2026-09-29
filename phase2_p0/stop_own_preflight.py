"""Interrupt only the identified earlier P0 inventory, which had a slow glob."""
import os,signal
from pathlib import Path
pid=726364
p=Path('/proc')/str(pid)
if p.exists():
    cmd=(p/'cmdline').read_bytes()
    status=(p/'status').read_text()
    ppid=int(next(l for l in status.splitlines() if l.startswith('PPid:')).split()[1])
    parent=(Path('/proc')/str(ppid)/'cmdline').read_bytes()
    assert cmd.endswith(b'/env/bin/python\x00-\x00'),repr(cmd)
    assert b'IiIiUmVhZC1vbmx5IHNlcnZlciBpbnZlbnRvcnk7' in parent
    os.kill(pid,signal.SIGINT)
    print('Interrupted own P0 inventory pid',pid)
