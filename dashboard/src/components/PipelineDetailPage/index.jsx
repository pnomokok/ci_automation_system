import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  formatApiError, formatDate, formatDuration,
  getPipeline, getPipelineReport, retriggerPipeline, stopPipeline,
} from '../../services/api';
import LogViewer from '../LogViewer';
import StatusBadge from '../StatusBadge';

function MetaRow({ label, children }) {
  return (
    <div className="flex gap-3 py-2 border-b border-dark-700 last:border-b-0">
      <span className="text-gray-500 text-sm w-36 shrink-0">{label}</span>
      <span className="text-gray-200 text-sm font-mono break-all">{children}</span>
    </div>
  );
}

function StepRow({ step }) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 border-b border-dark-700 last:border-b-0">
      <span className="text-gray-300 font-mono text-sm w-16">{step.order}.</span>
      <span className="text-gray-200 font-mono text-sm w-20">{step.name}</span>
      <StatusBadge status={step.status} size="sm" />
      <span className="text-gray-500 text-sm ml-auto font-mono">{formatDuration(step.duration_sec)}</span>
      {step.exit_code != null && (
        <span className={`text-xs font-mono ${step.exit_code === 0 ? 'text-green-400' : 'text-red-400'}`}>
          exit {step.exit_code}
        </span>
      )}
    </div>
  );
}

export default function PipelineDetailPage() {
  const { repoId, id } = useParams();
  const navigate = useNavigate();
  const backTo = repoId ? `/repositories/${repoId}` : '/repositories';

  const [pipeline, setPipeline] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stopping, setStopping] = useState(false);
  const [retriggering, setRetriggering] = useState(false);
  const pollRef = useRef(null);

  const fetchPipeline = useCallback(async () => {
    try {
      const res = await getPipeline(id);
      setPipeline(res.data);
      setError('');
      if (res.data.status === 'SUCCESS' || res.data.status === 'FAILED') {
        try {
          const rep = await getPipelineReport(id);
          setReport(rep.data);
        } catch { /* report endpoint may not exist */ }
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchPipeline(); }, [fetchPipeline]);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pipeline?.status === 'RUNNING') {
      pollRef.current = setInterval(fetchPipeline, 5000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pipeline?.status, fetchPipeline]);

  const handleRetrigger = async () => {
    if (!window.confirm('Aynı branch için yeni bir pipeline başlatılsın mı?')) return;
    setRetriggering(true);
    try {
      const res = await retriggerPipeline(id);
      const newId = res.data.id;
      if (repoId) {
        navigate(`/repositories/${repoId}/pipelines/${newId}`);
      } else {
        navigate(`/pipelines/${newId}`);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setRetriggering(false);
    }
  };

  const handleStop = async () => {
    if (!window.confirm('Pipeline durdurulsun mu?')) return;
    setStopping(true);
    try {
      await stopPipeline(id);
      await fetchPipeline();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setStopping(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !pipeline) {
    return (
      <div className="bg-red-950 border border-red-800 text-red-300 rounded-lg px-5 py-4 text-sm">
        {error}
        <Link to={backTo} className="ml-3 underline hover:no-underline">← Geri dön</Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-500">
        <Link to="/repositories" className="hover:text-gray-300 transition-colors">Repositories</Link>
        {repoId && (
          <>
            <span>›</span>
            <Link to={`/repositories/${repoId}`} className="hover:text-gray-300 transition-colors font-mono">
              {repoId.slice(0, 8)}…
            </Link>
          </>
        )}
        <span>›</span>
        <span className="text-gray-400 font-mono">Pipeline {id?.slice(0, 8)}…</span>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={backTo} className="text-gray-500 hover:text-gray-200 text-sm transition-colors">
          ← Geri
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-gray-100">Pipeline</h1>
          <span className="text-gray-600 font-mono text-sm">{id.slice(0, 8)}…</span>
          {pipeline && <StatusBadge status={pipeline.status} />}
        </div>
        <div className="flex-1" />
        {pipeline && ['SUCCESS', 'FAILED', 'STOPPED'].includes(pipeline.status) && (
          <button
            onClick={handleRetrigger}
            disabled={retriggering}
            className="bg-blue-800/60 hover:bg-blue-700/80 border border-blue-700 text-blue-200
                       text-sm px-3 py-1.5 rounded-md disabled:opacity-60 transition-colors"
          >
            {retriggering ? 'Tetikleniyor…' : '↺ Yeniden Tetikle'}
          </button>
        )}
        {pipeline?.status === 'RUNNING' && (
          <button
            onClick={handleStop}
            disabled={stopping}
            className="bg-red-800/60 hover:bg-red-700/80 border border-red-700 text-red-200
                       text-sm px-3 py-1.5 rounded-md disabled:opacity-60 transition-colors"
          >
            {stopping ? 'Durduruluyor…' : '■ Durdur'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {pipeline?.status === 'FAILED' &&
       pipeline.steps?.length > 0 &&
       pipeline.steps.every(s => s.status === 'PENDING') && (
        <div className="flex items-start gap-3 bg-yellow-950/50 border border-yellow-800/60 rounded-md px-4 py-3">
          <span className="text-yellow-400 text-base mt-0.5">⚠</span>
          <div>
            <p className="text-yellow-300 text-sm font-medium">Pipeline başlamadan önce başarısız oldu</p>
            <p className="text-yellow-500 text-xs mt-1">
              Hiçbir adım çalıştırılmadı. Bunun en yaygın nedeni repoda{' '}
              <code className="font-mono bg-dark-800 px-1 rounded">ci-config.yaml</code>{' '}
              dosyasının bulunmamasıdır. Bu dosyayı varsayılan branch'e ekleyip pipeline'ı yeniden tetikleyin.
            </p>
          </div>
        </div>
      )}

      {pipeline && (
        <>
          <div className="bg-dark-900 border border-dark-600 rounded-lg px-4 py-1">
            <MetaRow label="Repository">{pipeline.repo_url || '—'}</MetaRow>
            <MetaRow label="Branch">{pipeline.branch || '—'}</MetaRow>
            {pipeline.commit_hash && (
              <MetaRow label="Commit">{pipeline.commit_hash.slice(0, 12)} — {pipeline.commit_msg}</MetaRow>
            )}
            {pipeline.commit_author && (
              <MetaRow label="Yazar">{pipeline.commit_author}</MetaRow>
            )}
            <MetaRow label="Tetikleyen">
              {pipeline.triggered_by_username || (pipeline.trigger_type === 'webhook' ? 'Sistem' : '—')}
            </MetaRow>
            <MetaRow label="Tetikleme">
              {pipeline.trigger_type === 'webhook' ? '🔗 Webhook' : 'Manuel'}
            </MetaRow>
            <MetaRow label="Başlangıç">{formatDate(pipeline.started_at)}</MetaRow>
            <MetaRow label="Bitiş">{formatDate(pipeline.finished_at)}</MetaRow>
            <MetaRow label="Süre">{formatDuration(pipeline.duration_sec)}</MetaRow>
          </div>

          {pipeline.steps?.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Adımlar</h2>
              <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
                {pipeline.steps.map((step) => <StepRow key={step.id} step={step} />)}
              </div>
            </div>
          )}

          {report && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Test Raporu</h2>
              {report.no_tests_found ? (
                <div className="flex items-start gap-3 bg-yellow-950/50 border border-yellow-800/60 rounded-md px-4 py-3">
                  <span className="text-yellow-400 text-base mt-0.5">⚠</span>
                  <div>
                    <p className="text-yellow-300 text-sm font-medium">Test adımı çalıştı ancak hiçbir test bulunamadı</p>
                    <p className="text-yellow-500 text-xs mt-1">
                      Pipeline başarıyla tamamlandı fakat test sonuçları raporlanamadı.{' '}
                      <code className="font-mono bg-dark-800 px-1 rounded">tests/</code>{' '}
                      klasörüne test dosyaları ekleyerek CI güvenilirliğini artırabilirsin.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="bg-dark-900 border border-dark-600 rounded-lg px-5 py-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-100">{report.total_tests}</div>
                    <div className="text-xs text-gray-500 mt-0.5">Toplam</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{report.passed}</div>
                    <div className="text-xs text-gray-500 mt-0.5">Geçti</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-400">{report.failed}</div>
                    <div className="text-xs text-gray-500 mt-0.5">Başarısız</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-400">{report.skipped}</div>
                    <div className="text-xs text-gray-500 mt-0.5">Atlandı</div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Loglar</h2>
            <LogViewer pipelineId={id} />
          </div>
        </>
      )}
    </div>
  );
}
