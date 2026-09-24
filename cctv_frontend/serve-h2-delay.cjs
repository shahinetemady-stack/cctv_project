// Minimal static HTTP/2 server with gzip for local Lighthouse testing (mirrors nginx h2+gzip)
const http2 = require('http2')
const fs = require('fs')
const path = require('path')
const zlib = require('zlib')

const root = path.join(__dirname, 'dist')
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css',
  '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml',
}
const compressible = /text\/|application\/(javascript|json|manifest|xml)|image\/svg|font\//

const CSS_DELAY = parseInt(process.env.CSS_DELAY_MS || '0', 10)
const server = http2.createSecureServer({
  key: fs.readFileSync('/tmp/lh/key.pem'),
  cert: fs.readFileSync('/tmp/lh/cert.pem'),
})

server.on('stream', async (stream, headers) => {
  let p = decodeURIComponent(headers[':path'].split('?')[0])
  if (p.endsWith('/')) p += 'index.html'
  let file = path.join(root, p)
  if (!file.startsWith(root)) { stream.respond({ ':status': 403 }); return stream.end() }
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    if (/\.json$/.test(p)) { stream.respond({ ':status': 404 }); return stream.end('not found') }
    file = path.join(root, 'index.html')
  }
  const ext = path.extname(file)
  if (CSS_DELAY && ext === '.css') await new Promise(r => setTimeout(r, CSS_DELAY))
  const type = types[ext] || 'application/octet-stream'
  const data = fs.readFileSync(file)
  const h = { 'content-type': type, 'cache-control': ext === '.html' ? 'no-cache' : 'public, max-age=2592000, immutable' }
  const ae = headers['accept-encoding'] || ''
  if (data.length > 1024 && compressible.test(type) && ae.includes('gzip')) {
    h['content-encoding'] = 'gzip'
    h['vary'] = 'accept-encoding'
    stream.respond(h)
    zlib.gzip(data, { level: 5 }, (err, out) => stream.end(out))
  } else {
    stream.respond(h)
    stream.end(data)
  }
})

server.listen(process.env.PORT || 4175, '127.0.0.1', () => console.log('h2 server on', process.env.PORT || 4175))
