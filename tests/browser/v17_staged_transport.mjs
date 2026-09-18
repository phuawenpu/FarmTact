/** Operator-only Playwright transport. No listening port or public proxy is created.
 * Exact candidate assets and API responses arrive over authenticated Fly SSH.
 * Gateway credentials stay inside the remote process; cookies stay in memory.
 */
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';

const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
const normalizeEdition = value => {
  const edition = String(value || 'v19').toLowerCase().replace(/^v?/, 'v');
  if (!/^v(?:15|16|17|18|19)$/.test(edition)) throw Error('EXPECTED_EDITION must be v15 through v19');
  return edition;
};
const expectedEdition = normalizeEdition(process.env.EXPECTED_EDITION);
const sshContainer = process.env.STAGED_CONTAINER || expectedEdition;
const remotePort = Number(process.env.STAGED_PORT || (8080 + Number(expectedEdition.slice(1))));
if (sshContainer !== expectedEdition) throw Error('STAGED_CONTAINER must match EXPECTED_EDITION');
if (![8095, 8096, 8097, 8098, 8099].includes(remotePort) || remotePort !== (8080 + Number(expectedEdition.slice(1)))) throw Error('STAGED_PORT does not match the expected edition');

function remote(code, input = '') {
  return new Promise((resolve, reject) => {
    const child = spawn('fly', ['ssh', 'console', '--app', 'farmtact', '--machine', '2871575b4544d8', '--container', sshContainer, '--quiet', '--command', 'python -c ' + quote(code)], { stdio: ['pipe', 'pipe', 'pipe'] });
    const output = []; let bytes = 0;
    const timer = setTimeout(() => child.kill('SIGTERM'), 180_000);
    child.stdout.on('data', data => { bytes += data.length; if (bytes > 40_000_000) child.kill('SIGTERM'); else output.push(data); });
    // SSH output can contain response cookies. Never include it in errors/logs.
    child.stderr.resume();
    child.on('error', () => { clearTimeout(timer); reject(Error('Private candidate SSH unavailable')); });
    child.on('close', code => { clearTimeout(timer); if (code !== 0) reject(Error('Private candidate SSH failed; request was not retried')); else { try { resolve(JSON.parse(Buffer.concat(output).toString())); } catch { reject(Error('Invalid private candidate transport response')); } } });
    child.stdin.on('error', () => {}); child.stdin.end(input);
  });
}

export async function stagedTransport(expectedSource) {
  if (!/^[0-9a-f]{40}$/.test(expectedSource || '')) throw Error('Full staged source identity required');
  const artifact = await remote(`import base64,hashlib,json,mimetypes,httpx,os
from pathlib import Path
root=Path('/app/apps/web/dist')
files={}
for p in root.rglob('*'):
 if p.is_file() and not p.is_symlink():
  data=p.read_bytes()
  files['/'+p.relative_to(root).as_posix()]={'body':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest(),'type':mimetypes.guess_type(str(p))[0] or 'application/octet-stream'}
health=httpx.get('http://127.0.0.1:${remotePort}/api/v1/health',timeout=15,trust_env=False).json()
response=httpx.get('http://127.0.0.1:${remotePort}/',headers={'host':'farmtact.fly.dev','x-farmtact-gateway':os.environ['FARMTACT_CONTROL_SECRET'],'x-farmtact-client-ip':'127.0.0.1'},timeout=15,trust_env=False)
assert response.status_code==200 and hashlib.sha256(response.content).hexdigest()==files['/index.html']['sha256']
headers={k:v for k,v in response.headers.items() if k.lower() not in ('content-encoding','content-length','transfer-encoding','connection','set-cookie','etag','last-modified','content-type')}
print(json.dumps({'source':Path('/app/config/build-source.txt').read_text().strip(),'files':files,'health':health,'document_headers':headers}))`);
  if (artifact.source !== expectedSource || artifact.health?.source_commit !== expectedSource || artifact.health?.edition !== expectedEdition || artifact.health?.status !== 'ok' || !artifact.files['/index.html']) throw Error('Staged artifact/runtime source mismatch');
  const requestCode = `import base64,json,os,sys,httpx
from urllib.parse import urlsplit
item=json.load(sys.stdin)
path=item['path']; parsed=urlsplit(path)
assert parsed.path.startswith('/api/v1/') and not parsed.netloc and not parsed.scheme
assert item['method'] in ('GET','POST','HEAD')
if item['method']=='POST':
 assert parsed.path.startswith(('/api/v1/planning-sessions','/api/v1/farm-workflow/'))
 assert not any(x in parsed.path for x in ('/review','/council','/messages','/invite','/extract'))
headers={k:v for k,v in item['headers'].items() if k.lower() in ('cookie','content-type','idempotency-key','accept')}
headers.update({'host':'farmtact.fly.dev','origin':'https://farmtact.fly.dev','x-farmtact-gateway':os.environ['FARMTACT_CONTROL_SECRET'],'x-farmtact-client-ip':'127.0.0.1'})
with httpx.Client(timeout=120,trust_env=False) as c:
 r=c.request(item['method'],'http://127.0.0.1:${remotePort}'+path,headers=headers,content=base64.b64decode(item['body']))
 safe={k:v for k,v in r.headers.items() if k.lower() not in ('content-encoding','content-length','transfer-encoding','connection')}
 print(json.dumps({'status':r.status_code,'headers':safe,'body':base64.b64encode(r.content).decode()}))`;
  const traffic = []; const failures = [];
  return {
    evidence: { source_commit: artifact.source, edition: artifact.health.edition, content_security_policy: artifact.document_headers['content-security-policy'] || null, asset_sha256: Object.fromEntries(Object.entries(artifact.files).map(([path, f]) => [path, f.sha256])), transport: 'authenticated Fly SSH; exact image assets and document security headers; fixed loopback API', traffic, failures },
    async attach(context) {
      await context.route('**/*', async route => {
        try {
          const request = route.request(), url = new URL(request.url());
          if (url.origin !== 'http://127.0.0.1:4199') return route.abort('blockedbyclient');
          if (url.pathname.startsWith('/api/v1/')) {
            const headers = await request.allHeaders();
            const response = await remote(requestCode, JSON.stringify({ method: request.method(), path: url.pathname + url.search, headers, body: request.postDataBuffer()?.toString('base64') || '' }));
            traffic.push({ method: request.method(), path: url.pathname, status: response.status });
            // Local browser origin uses HTTP; the upstream production cookie remains secure.
            if (response.headers['set-cookie']) response.headers['set-cookie'] = response.headers['set-cookie'].replace(/;\s*Secure/gi, '');
            await route.fulfill({ status: response.status, headers: response.headers, body: Buffer.from(response.body, 'base64') });
          } else {
            const path = ['/', '/play'].includes(url.pathname) ? '/index.html' : url.pathname;
            const file = artifact.files[path];
            if (!file) return route.fulfill({ status: 404, body: 'Not found' });
            const body = Buffer.from(file.body, 'base64');
            if (createHash('sha256').update(body).digest('hex') !== file.sha256) throw Error('Staged asset digest mismatch');
            await route.fulfill({ status: 200, headers: artifact.document_headers, contentType: file.type, body });
          }
        } catch (error) { failures.push(String(error)); await route.abort('failed').catch(() => {}); }
      });
    },
  };
}
