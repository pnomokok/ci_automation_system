import { useCallback, useEffect, useRef, useState } from 'react';
import { formatApiError, getPipelineLogs } from '../../services/api';

async function fetchAllLogs(pipelineId, stepName, streamFilter) {
  const allLines = [];
  let page = 1;
  const pageSize = 500;
  while (true) {
    const params = { step_name: stepName, page, page_size: pageSize };
    if (streamFilter) params.stream = streamFilter;
    const res = await getPipelineLogs(pipelineId, params);
    const { items, total } = res.data;
    allLines.push(...items);
    if (allLines.length >= total) break;
    page++;
  }
  return allLines;
}

const STEPS = ['install', 'build', 'test'];
const PAGE_SIZE = 100;

function highlight(content, query) {
  if (!query) return content;
  const parts = content.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase()
      ? <mark key={i} className="bg-yellow-600/40 text-yellow-200 rounded-sm">{part}</mark>
      : part
  );
}

export default function LogViewer({ pipelineId }) {
  const [activeStep, setActiveStep] = useState('install');
  const [streamFilter, setStreamFilter] = useState('');
  const [search, setSearch] = useState('');
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fetchLogs = useCallback(async () => {
    if (!pipelineId) return;
    setLoading(true);
    setError('');
    try {
      const params = { step_name: activeStep, page, page_size: PAGE_SIZE };
      if (streamFilter) params.stream = streamFilter;
      const res = await getPipelineLogs(pipelineId, params);
      setLogs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [pipelineId, activeStep, streamFilter, page]);

  useEffect(() => {
    setPage(1);
  }, [activeStep, streamFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const filteredLogs = search
    ? logs.filter((l) => l.content.toLowerCase().includes(search.toLowerCase()))
    : logs;

  const handleCopy = () => {
    const text = filteredLogs.map((l) => l.content).join('\n');
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const lines = await fetchAllLogs(pipelineId, activeStep, streamFilter);
      const text = lines.map((l) => l.content).join('\n');
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pipeline-${pipelineId.slice(0, 8)}-${activeStep}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-dark-600 flex-wrap">
        {/* Step tabs */}
        <div className="flex rounded-md overflow-hidden border border-dark-600">
          {STEPS.map((step) => (
            <button
              key={step}
              onClick={() => setActiveStep(step)}
              className={`px-3 py-1 text-xs font-mono transition-colors ${
                activeStep === step
                  ? 'bg-blue-700 text-white'
                  : 'bg-dark-800 text-gray-400 hover:text-gray-200'
              }`}
            >
              {step}
            </button>
          ))}
        </div>

        {/* Stream filter */}
        <select
          value={streamFilter}
          onChange={(e) => setStreamFilter(e.target.value)}
          className="bg-dark-800 border border-dark-600 text-gray-400 text-xs rounded px-2 py-1
                     focus:outline-none focus:border-blue-500"
        >
          <option value="">stdout + stderr</option>
          <option value="stdout">stdout</option>
          <option value="stderr">stderr</option>
        </select>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Ara…"
          className="bg-dark-800 border border-dark-600 text-gray-300 text-xs rounded px-2 py-1
                     focus:outline-none focus:border-blue-500 w-36"
        />

        <div className="flex-1" />

        <span className="text-gray-600 text-xs font-mono">{total} satır</span>

        {/* Copy */}
        <button
          onClick={handleCopy}
          className="text-xs text-gray-500 hover:text-gray-200 transition-colors px-2 py-1
                     bg-dark-800 border border-dark-600 rounded"
        >
          {copied ? '✓ Kopyalandı' : 'Kopyala'}
        </button>

        {/* Export */}
        <button
          onClick={handleExport}
          disabled={exporting}
          className="text-xs text-gray-500 hover:text-gray-200 transition-colors px-2 py-1
                     bg-dark-800 border border-dark-600 rounded disabled:opacity-50"
        >
          {exporting ? '…' : '↓ Dışa Aktar'}
        </button>
      </div>

      {/* Log output */}
      <div className="bg-dark-950 overflow-auto max-h-[480px]">
        {loading ? (
          <div className="flex items-center justify-center py-10 text-gray-600 text-sm">Yükleniyor…</div>
        ) : error ? (
          <div className="px-4 py-4 text-red-400 text-sm">{error}</div>
        ) : filteredLogs.length === 0 ? (
          <div className="px-4 py-8 text-gray-600 text-sm text-center">
            {search ? 'Aramayla eşleşen satır bulunamadı.' : `"${activeStep}" adımı için log yok.`}
          </div>
        ) : (
          <table className="w-full log-content">
            <tbody>
              {filteredLogs.map((line) => (
                <tr
                  key={`${line.step_id}-${line.line_number}`}
                  className={`hover:bg-dark-900/50 ${line.stream === 'stderr' ? 'text-red-300' : 'text-gray-300'}`}
                >
                  <td className="text-gray-700 select-none text-right pr-3 pl-4 py-0.5 w-12 align-top">
                    {line.line_number}
                  </td>
                  <td className="text-gray-700 pr-3 py-0.5 w-14 align-top whitespace-nowrap">
                    {line.stream === 'stderr' ? (
                      <span className="text-red-700">err</span>
                    ) : (
                      <span className="text-gray-700">out</span>
                    )}
                  </td>
                  <td className="pr-4 py-0.5 break-all whitespace-pre-wrap">
                    {highlight(line.content, search)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-dark-600 bg-dark-900">
          <span className="text-xs text-gray-600 font-mono">
            {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} / {total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-2 py-0.5 text-xs bg-dark-800 border border-dark-600 rounded text-gray-400
                         hover:text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ‹ Önceki
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-2 py-0.5 text-xs bg-dark-800 border border-dark-600 rounded text-gray-400
                         hover:text-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Sonraki ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
