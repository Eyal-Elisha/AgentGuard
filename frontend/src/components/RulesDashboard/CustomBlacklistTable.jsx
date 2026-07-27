export default function CustomBlacklistTable({ entries, isLoading, isUpdating, onDeleteClick }) {
  if (isLoading) {
    return (
      <div className="rules-table-wrapper">
        <table className="rules-table">
          <tbody>
            <tr className="rules-empty-row">
              <td className="rules-empty-state">Loading blacklist...</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="rules-table-wrapper">
      <div className="rules-table-scroll" style={{ maxHeight: '400px' }}>
        <table className="rules-table">
          <thead>
            <tr>
              <th style={{ width: '100%' }}>DOMAIN</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr className="rules-empty-row">
                <td colSpan={2} className="rules-empty-state">
                  The custom blacklist is empty. No domains are currently blocked by this policy.
                </td>
              </tr>
            ) : (
              entries.map((domain) => (
                <tr key={domain}>
                  <td className="custom-blacklist-domain">{domain}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="custom-blacklist-delete-btn"
                      onClick={() => onDeleteClick(domain)}
                      disabled={isUpdating}
                      aria-label={`Remove ${domain}`}
                      title="Remove domain"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        <line x1="10" y1="11" x2="10" y2="17"/>
                        <line x1="14" y1="11" x2="14" y2="17"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
