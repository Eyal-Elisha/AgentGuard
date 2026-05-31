import { useState } from 'react';
import './EventMetadata.css';

const METHOD_COLOR = {
  GET: 'get', POST: 'post', PUT: 'put', PATCH: 'patch',
  DELETE: 'delete', OPTIONS: 'options', HEAD: 'head',
};

function HeadersTable({ headers }) {
  const entries = headers && typeof headers === 'object' ? Object.entries(headers) : [];
  if (entries.length === 0) return <p className="event-meta-empty">No headers recorded.</p>;
  return (
    <dl className="event-meta-kv-table">
      {entries.map(([key, val]) => (
        <div key={key} className="event-meta-kv-row">
          <dt className="event-meta-kv-key">{key}</dt>
          <dd className="event-meta-kv-val">{String(val)}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function EventMetadata({ url, http_method, headers }) {
  const [headersOpen, setHeadersOpen] = useState(false);
  const methodKey = (http_method || '').toUpperCase();
  const methodColor = METHOD_COLOR[methodKey] || 'default';

  return (
    <div className="event-meta-section">
      <div className="event-meta-row">
        {http_method && (
          <span className={`event-meta-method-badge event-meta-method-badge--${methodColor}`}>
            {methodKey}
          </span>
        )}
        <span className="event-meta-url" title={url}>{url || '–'}</span>
      </div>

      <div className="event-meta-headers">
        <button
          type="button"
          className="event-meta-headers-toggle"
          onClick={() => setHeadersOpen((o) => !o)}
          aria-expanded={headersOpen}
        >
          {headersOpen ? '▾' : '▸'} Request Headers
          {headers && typeof headers === 'object' && (
            <span className="event-meta-headers-count">({Object.keys(headers).length})</span>
          )}
        </button>
        {headersOpen && <HeadersTable headers={headers} />}
      </div>
    </div>
  );
}
