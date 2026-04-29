const CONFIG = {
  QUEUED:   { label: 'QUEUED',   cls: 'bg-amber-900/40 text-amber-300 border-amber-700' },
  RUNNING:  { label: 'RUNNING',  cls: 'bg-blue-900/40  text-blue-300  border-blue-700 animate-pulse-slow' },
  SUCCESS:  { label: 'SUCCESS',  cls: 'bg-green-900/40 text-green-300 border-green-700' },
  FAILED:   { label: 'FAILED',   cls: 'bg-red-900/40   text-red-300   border-red-700' },
  STOPPED:  { label: 'STOPPED',  cls: 'bg-gray-800/60  text-gray-400  border-gray-600' },
};

const STEP_CONFIG = {
  PENDING:  { label: 'PENDING',  cls: 'bg-gray-800/60  text-gray-400  border-gray-600' },
  RUNNING:  { label: 'RUNNING',  cls: 'bg-blue-900/40  text-blue-300  border-blue-700 animate-pulse-slow' },
  SUCCESS:  { label: 'SUCCESS',  cls: 'bg-green-900/40 text-green-300 border-green-700' },
  FAILED:   { label: 'FAILED',   cls: 'bg-red-900/40   text-red-300   border-red-700' },
};

export default function StatusBadge({ status, size = 'md' }) {
  const cfg = CONFIG[status] || STEP_CONFIG[status] || {
    label: status || '—',
    cls: 'bg-gray-800/60 text-gray-400 border-gray-600',
  };

  const sizeCls = size === 'sm'
    ? 'text-xs px-1.5 py-0.5'
    : 'text-xs px-2.5 py-1 font-medium';

  return (
    <span
      className={`inline-flex items-center rounded border font-mono tracking-wide ${sizeCls} ${cfg.cls}`}
    >
      {cfg.label}
    </span>
  );
}
