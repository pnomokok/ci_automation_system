/**
 * CI Dashboard — Mock API Sunucusu
 * Çalıştır: node mock-server.cjs
 * Sonra başka terminalde: npm run dev
 * Giriş: kullanıcı adı "admin", şifre "password"
 */

const http = require('http');

// ── Yardımcı: sahte JWT üret ────────────────────────────────────
function fakeJwt(username) {
  const enc = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');
  const header  = enc({ alg: 'HS256', typ: 'JWT' });
  const payload = enc({ sub: 'user-001', username, exp: Math.floor(Date.now() / 1000) + 3600 });
  return `${header}.${payload}.mock-signature`;
}

// ── Mock veri ───────────────────────────────────────────────────
let pipelines = [
  {
    id: 'pl-001', repo_id: 'repo-001',
    repo_url: 'https://github.com/pnomokok/ci_automation_system',
    branch: 'main', commit_hash: 'a55f6b6c3d',
    commit_msg: 'feat(runner): Docker container yönetimi tamamlandı',
    commit_author: 'Aleyna Yılmaz', trigger_type: 'webhook', status: 'SUCCESS',
    started_at: '2026-04-29T08:00:00.000Z', finished_at: '2026-04-29T08:04:30.000Z', duration_sec: 270,
  },
  {
    id: 'pl-002', repo_id: 'repo-001',
    repo_url: 'https://github.com/pnomokok/ci_automation_system',
    branch: 'develop', commit_hash: 'b7e8f9a1b2',
    commit_msg: 'fix(orchestrator): Redis kuyruk bağlantısı düzeltildi',
    commit_author: 'Irmak Su', trigger_type: 'webhook', status: 'FAILED',
    started_at: '2026-04-29T09:15:00.000Z', finished_at: '2026-04-29T09:16:45.000Z', duration_sec: 105,
  },
  {
    id: 'pl-003', repo_id: 'repo-001',
    repo_url: 'https://github.com/pnomokok/ci_automation_system',
    branch: 'feature/repo-manager', commit_hash: 'c1d2e3f4a5',
    commit_msg: 'feat(repo-manager): Webhook HMAC doğrulaması eklendi',
    commit_author: 'Zeynep Sude', trigger_type: 'webhook', status: 'RUNNING',
    started_at: new Date().toISOString(), finished_at: null, duration_sec: null,
  },
  {
    id: 'pl-004', repo_id: 'repo-001',
    repo_url: 'https://github.com/pnomokok/ci_automation_system',
    branch: 'feature/web-dashboard', commit_hash: 'e022bdd4f5',
    commit_msg: 'feat(dashboard): React CI Dashboard implementasyonu',
    commit_author: 'Rabia Saldıran', trigger_type: 'manual', status: 'QUEUED',
    started_at: null, finished_at: null, duration_sec: null,
  },
  {
    id: 'pl-005', repo_id: 'repo-001',
    repo_url: 'https://github.com/pnomokok/ci_automation_system',
    branch: 'main', commit_hash: 'd4e5f6a7b8',
    commit_msg: 'chore: Docker Compose ortamı güncellendi',
    commit_author: 'Irmak Su', trigger_type: 'manual', status: 'STOPPED',
    started_at: '2026-04-28T15:00:00.000Z', finished_at: '2026-04-28T15:02:10.000Z', duration_sec: 130,
  },
];

const steps = {
  'pl-001': [
    { id: 'st-001-1', name: 'install', order: 1, status: 'SUCCESS', started_at: '2026-04-29T08:00:05.000Z', finished_at: '2026-04-29T08:01:45.000Z', duration_sec: 100, exit_code: 0 },
    { id: 'st-001-2', name: 'build',   order: 2, status: 'SUCCESS', started_at: '2026-04-29T08:01:46.000Z', finished_at: '2026-04-29T08:02:30.000Z', duration_sec: 44,  exit_code: 0 },
    { id: 'st-001-3', name: 'test',    order: 3, status: 'SUCCESS', started_at: '2026-04-29T08:02:31.000Z', finished_at: '2026-04-29T08:04:30.000Z', duration_sec: 119, exit_code: 0 },
  ],
  'pl-002': [
    { id: 'st-002-1', name: 'install', order: 1, status: 'SUCCESS', started_at: '2026-04-29T09:15:05.000Z', finished_at: '2026-04-29T09:16:00.000Z', duration_sec: 55, exit_code: 0 },
    { id: 'st-002-2', name: 'build',   order: 2, status: 'FAILED',  started_at: '2026-04-29T09:16:01.000Z', finished_at: '2026-04-29T09:16:45.000Z', duration_sec: 44, exit_code: 1 },
    { id: 'st-002-3', name: 'test',    order: 3, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
  ],
  'pl-003': [
    { id: 'st-003-1', name: 'install', order: 1, status: 'SUCCESS', started_at: new Date(Date.now()-90000).toISOString(), finished_at: new Date(Date.now()-30000).toISOString(), duration_sec: 60, exit_code: 0 },
    { id: 'st-003-2', name: 'build',   order: 2, status: 'RUNNING', started_at: new Date(Date.now()-30000).toISOString(), finished_at: null, duration_sec: null, exit_code: null },
    { id: 'st-003-3', name: 'test',    order: 3, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
  ],
  'pl-004': [
    { id: 'st-004-1', name: 'install', order: 1, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
    { id: 'st-004-2', name: 'build',   order: 2, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
    { id: 'st-004-3', name: 'test',    order: 3, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
  ],
  'pl-005': [
    { id: 'st-005-1', name: 'install', order: 1, status: 'SUCCESS', started_at: '2026-04-28T15:00:05.000Z', finished_at: '2026-04-28T15:01:10.000Z', duration_sec: 65, exit_code: 0 },
    { id: 'st-005-2', name: 'build',   order: 2, status: 'STOPPED', started_at: '2026-04-28T15:01:11.000Z', finished_at: '2026-04-28T15:02:10.000Z', duration_sec: 59, exit_code: null },
    { id: 'st-005-3', name: 'test',    order: 3, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
  ],
};

const LOGS = {
  install: [
    'Collecting dependencies from requirements.txt...',
    'Downloading flask-3.0.0-py3-none-any.whl (101 kB)',
    'Downloading redis-5.0.1-py3-none-any.whl (250 kB)',
    'Downloading sqlalchemy-2.0.30-cp311-cp311-linux_x86_64.whl (3.1 MB)',
    'Downloading alembic-1.13.0-py3-none-any.whl (233 kB)',
    'Downloading pydantic-2.7.0-cp311-cp311-linux_x86_64.whl (2.6 MB)',
    'Downloading uvicorn-0.30.0-py3-none-any.whl (62 kB)',
    'Installing collected packages: flask, redis, sqlalchemy, alembic, pydantic, uvicorn',
    'Successfully installed all packages.',
  ],
  build: [
    'Running pre-build checks...',
    'Checking module imports...',
    'Verifying configuration...',
    'No build step required for Python project.',
    'Build check completed successfully.',
  ],
  test: [
    '==================== test session starts ====================',
    'platform linux -- Python 3.11.9, pytest-8.3.3, pluggy-1.5.0',
    'rootdir: /workspace',
    'configfile: pytest.ini',
    'collected 24 items',
    '',
    'tests/test_auth.py ....                                [ 16%]',
    'tests/test_pipelines.py ..........                     [ 58%]',
    'tests/test_repositories.py ......                      [ 83%]',
    'tests/test_internal.py ....                            [100%]',
    '',
    '==================== 24 passed in 18.40s ====================',
  ],
};

function buildLogs(pipelineId, stepName) {
  const pipeline = pipelines.find(p => p.id === pipelineId);
  const pSteps   = steps[pipelineId] || [];
  const step     = pSteps.find(s => s.name === stepName);
  if (!step) return [];

  const lines = LOGS[stepName] || ['No logs.'];
  // For FAILED build, inject an error
  if (pipelineId === 'pl-002' && stepName === 'build') {
    return [
      { step_id: step.id, step_name: stepName, line_number: 1, stream: 'stdout', timestamp: new Date().toISOString(), content: 'Running build checks...' },
      { step_id: step.id, step_name: stepName, line_number: 2, stream: 'stderr', timestamp: new Date().toISOString(), content: 'ERROR: ConnectionRefusedError: [Errno 111] Connection refused' },
      { step_id: step.id, step_name: stepName, line_number: 3, stream: 'stderr', timestamp: new Date().toISOString(), content: 'ERROR: Redis connection failed at redis:6379' },
      { step_id: step.id, step_name: stepName, line_number: 4, stream: 'stdout', timestamp: new Date().toISOString(), content: 'Build FAILED with exit code 1' },
    ];
  }
  return lines.map((content, i) => ({
    step_id: step.id, step_name: stepName, line_number: i + 1,
    stream: 'stdout', timestamp: new Date(Date.now() - (lines.length - i) * 1200).toISOString(), content,
  }));
}

// ── HTTP Sunucusu ───────────────────────────────────────────────
function json(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Authorization,Content-Type' });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => { try { resolve(JSON.parse(body || '{}')); } catch { resolve({}); } });
  });
}

const server = http.createServer(async (req, res) => {
  const url    = new URL(req.url, 'http://localhost:8000');
  const path   = url.pathname;
  const method = req.method;

  // CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS', 'Access-Control-Allow-Headers': 'Authorization,Content-Type' });
    return res.end();
  }

  // ── Auth ────────────────────────────────────────────────────
  if (path === '/api/v1/auth/login' && method === 'POST') {
    const body = await readBody(req);
    if (body.username === 'admin' && body.password === 'password') {
      return json(res, 200, { access_token: fakeJwt(body.username), token_type: 'bearer', expires_in: 3600 });
    }
    return json(res, 401, { error: { code: 'UNAUTHORIZED', message: 'Kullanıcı adı veya şifre hatalı.' } });
  }

  if (path === '/api/v1/auth/refresh' && method === 'POST') {
    return json(res, 200, { access_token: fakeJwt('admin'), token_type: 'bearer', expires_in: 3600 });
  }

  // ── Pipelines listesi ───────────────────────────────────────
  if (path === '/api/v1/pipelines' && method === 'GET') {
    const statusFilter = url.searchParams.get('status');
    const page         = parseInt(url.searchParams.get('page') || '1');
    const pageSize     = parseInt(url.searchParams.get('page_size') || '20');
    let items = statusFilter ? pipelines.filter(p => p.status === statusFilter) : pipelines;
    const total = items.length;
    items = items.slice((page - 1) * pageSize, page * pageSize);
    return json(res, 200, { items, total, page, page_size: pageSize });
  }

  // ── Pipeline oluştur (manuel tetikleme) ─────────────────────
  if (path === '/api/v1/pipelines' && method === 'POST') {
    const body = await readBody(req);
    if (!body.repo_url || !body.branch) {
      return json(res, 400, { error: { code: 'INVALID_INPUT', message: 'repo_url ve branch zorunludur.' } });
    }
    const newPipeline = {
      id: `pl-${Date.now()}`, repo_id: 'repo-001',
      repo_url: body.repo_url, branch: body.branch,
      commit_hash: null, commit_msg: null, commit_author: null,
      trigger_type: 'manual', status: 'QUEUED',
      started_at: null, finished_at: null, duration_sec: null,
    };
    pipelines.unshift(newPipeline);
    steps[newPipeline.id] = [
      { id: `st-${Date.now()}-1`, name: 'install', order: 1, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
      { id: `st-${Date.now()}-2`, name: 'build',   order: 2, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
      { id: `st-${Date.now()}-3`, name: 'test',    order: 3, status: 'PENDING', started_at: null, finished_at: null, duration_sec: null, exit_code: null },
    ];
    return json(res, 201, { id: newPipeline.id, status: 'QUEUED', trigger_type: 'manual', branch: body.branch, created_at: new Date().toISOString() });
  }

  // ── Pipeline detay ──────────────────────────────────────────
  const detailMatch = path.match(/^\/api\/v1\/pipelines\/([^/]+)$/);
  if (detailMatch && method === 'GET') {
    const id = detailMatch[1];
    const pipeline = pipelines.find(p => p.id === id);
    if (!pipeline) return json(res, 404, { error: { code: 'PIPELINE_NOT_FOUND', message: 'Pipeline bulunamadı.' } });
    return json(res, 200, { ...pipeline, steps: steps[id] || [] });
  }

  // ── Pipeline durdur ─────────────────────────────────────────
  const stopMatch = path.match(/^\/api\/v1\/pipelines\/([^/]+)\/stop$/);
  if (stopMatch && method === 'POST') {
    const id = stopMatch[1];
    const pipeline = pipelines.find(p => p.id === id);
    if (!pipeline) return json(res, 404, { error: { code: 'PIPELINE_NOT_FOUND', message: 'Pipeline bulunamadı.' } });
    pipeline.status = 'STOPPED';
    pipeline.finished_at = new Date().toISOString();
    if (steps[id]) steps[id].forEach(s => { if (s.status === 'RUNNING' || s.status === 'PENDING') s.status = 'STOPPED'; });
    return json(res, 200, { id, status: 'STOPPED' });
  }

  // ── Pipeline logları ────────────────────────────────────────
  const logsMatch = path.match(/^\/api\/v1\/pipelines\/([^/]+)\/logs$/);
  if (logsMatch && method === 'GET') {
    const id       = logsMatch[1];
    const stepName = url.searchParams.get('step_name') || 'install';
    const page     = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '100');
    const stream   = url.searchParams.get('stream');
    let items = buildLogs(id, stepName);
    if (stream) items = items.filter(l => l.stream === stream);
    const total = items.length;
    items = items.slice((page - 1) * pageSize, page * pageSize);
    return json(res, 200, { pipeline_id: id, items, total, page, page_size: pageSize });
  }

  // ── Test raporu ─────────────────────────────────────────────
  const reportMatch = path.match(/^\/api\/v1\/pipelines\/([^/]+)\/report$/);
  if (reportMatch && method === 'GET') {
    const id = reportMatch[1];
    const pipeline = pipelines.find(p => p.id === id);
    if (!pipeline || pipeline.status !== 'SUCCESS') {
      return json(res, 404, { error: { code: 'PIPELINE_NOT_FOUND', message: 'Rapor mevcut değil.' } });
    }
    return json(res, 200, { pipeline_id: id, status: 'SUCCESS', total_tests: 24, passed: 24, failed: 0, skipped: 0, duration_sec: 18.4 });
  }

  // ── Repositories ────────────────────────────────────────────
  if (path === '/api/v1/repositories' && method === 'GET') {
    return json(res, 200, {
      items: [{ id: 'repo-001', url: 'https://github.com/pnomokok/ci_automation_system', default_branch: 'main', created_at: '2026-04-20T10:00:00Z' }],
      total: 1,
    });
  }

  // 404
  json(res, 404, { error: { code: 'NOT_FOUND', message: `${method} ${path} bulunamadı.` } });
});

server.listen(8000, () => {
  console.log('');
  console.log('  ✓ Mock API sunucusu çalışıyor → http://localhost:8000');
  console.log('');
  console.log('  Giriş bilgileri:');
  console.log('    Kullanıcı adı : admin');
  console.log('    Şifre         : password');
  console.log('');
  console.log('  Şimdi başka bir terminalde şunu çalıştır:');
  console.log('    cd dashboard && npm run dev');
  console.log('  Sonra aç: http://localhost:5173');
  console.log('');
});
