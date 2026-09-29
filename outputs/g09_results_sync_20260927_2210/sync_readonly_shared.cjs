// Read-only SSH transfer; no remote staging, writes, deletes, or GPU operations.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {spawnSync} = require('child_process');
const base = __dirname;
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
let files = 0, bytes = 0;
for (const dataset of ['mmke-visual', 'mmke-entity']) {
  const manifest = JSON.parse(fs.readFileSync(path.join(base, `manifest_${dataset}.json`), 'utf8'));
  for (const layer of manifest.layers) {
    if (!layer.complete) throw Error('Unverified layer');
    const dest = path.resolve(base, 'artifacts', dataset, layer.model, `layer_${String(layer.layer).padStart(2, '0')}`);
    if (!dest.startsWith(base + path.sep) || fs.existsSync(dest)) throw Error('Unsafe or existing destination');
    const stage = dest + '.partial';
    fs.mkdirSync(stage, {recursive: true});
    const missing = [];
    for (const a of layer.artifacts) {
      const target = path.join(stage, a.relative_path);
      if (path.dirname(target) !== stage) throw Error('Expected flattened artifact name');
      if (fs.existsSync(target)) {
        const data = fs.readFileSync(target);
        if (data.length !== a.size || hash(data) !== a.sha256) throw Error(`Existing partial mismatch: ${target}`);
      } else missing.push(a.path);
    }
    if (missing.length) {
      const remote = `import json,base64\npaths=json.loads(${JSON.stringify(JSON.stringify(missing))})\nprint(json.dumps([{'path':p,'data':base64.b64encode(open(p,'rb').read()).decode('ascii')} for p in paths]))\n`;
      const proc = spawnSync('ssh.exe', ['-i', path.join(process.env.USERPROFILE, '.ssh/id_ed25519_bridge'), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'bridge-server', 'python3', '-'], {input: remote, encoding: 'utf8', maxBuffer: 48*1024*1024, timeout: 180000, windowsHide: true});
      if (proc.status !== 0) throw Error(proc.stderr || 'SSH transfer failed');
      const received = JSON.parse(proc.stdout);
      if (received.length !== missing.length) throw Error('Artifact count mismatch');
      for (const item of received) {
        const a = layer.artifacts.find(a => a.path === item.path);
        if (!a || !missing.includes(item.path)) throw Error('Unexpected artifact');
        const data = Buffer.from(item.data, 'base64');
        if (data.length !== a.size || hash(data) !== a.sha256) throw Error(`Transferred hash mismatch: ${a.path}`);
        fs.writeFileSync(path.join(stage, a.relative_path), data, {flag:'wx'});
      }
    }
    for (const a of layer.artifacts) {
      const b = fs.readFileSync(path.join(stage, a.relative_path));
      if (b.length !== a.size || hash(b) !== a.sha256) throw Error('Final verification failed');
      files++; bytes += b.length;
    }
    fs.renameSync(stage, dest);
    console.log(JSON.stringify({dataset, model:layer.model, layer:layer.layer, verified_files:layer.artifacts.length, local:dest}));
  }
}
console.log(JSON.stringify({verified_files:files, verified_bytes:bytes, checkpoint_binaries_copied:false, remote_writes:false}));
