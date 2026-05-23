import { useState } from 'react';
import { useBlacklist } from '../../hooks/useBlacklist.js';
import { useAuth } from '../../context/AuthContext.jsx';
import DeleteDomainModal from './DeleteDomainModal.jsx';
import CustomBlacklistForm from './CustomBlacklistForm.jsx';
import CustomBlacklistTable from './CustomBlacklistTable.jsx';
import './CustomBlacklist.css';

export default function CustomBlacklist() {
  const { currentUser } = useAuth();
  const { entries, isLoading, isUpdating, error, addEntry, removeEntry } = useBlacklist();
  const [domainToDelete, setDomainToDelete] = useState(null);

  if (!currentUser?.isAdmin) {
    return null;
  }

  const confirmDelete = async () => {
    if (domainToDelete) {
      await removeEntry(domainToDelete);
      setDomainToDelete(null);
    }
  };

  return (
    <div id="custom-blacklist-section" className="custom-blacklist-container">
      <div className="custom-blacklist-header">
        <h2 className="custom-blacklist-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <path d="M15 9l-6 6"/>
            <path d="M9 9l6 6"/>
          </svg>
          Custom Domain Blacklist
        </h2>
        <p className="custom-blacklist-description">
          Add specific domains or URLs to strictly block them across all sessions.
        </p>
      </div>

      {error && (
        <div className="custom-blacklist-error" role="alert">
          {error}
        </div>
      )}

      <CustomBlacklistForm 
        onAdd={addEntry} 
        isLoading={isLoading} 
        isUpdating={isUpdating} 
      />

      <CustomBlacklistTable 
        entries={entries} 
        isLoading={isLoading} 
        isUpdating={isUpdating} 
        onDeleteClick={setDomainToDelete} 
      />

      {domainToDelete && (
        <DeleteDomainModal
          domain={domainToDelete}
          onConfirm={confirmDelete}
          onCancel={() => setDomainToDelete(null)}
          isPending={isUpdating}
        />
      )}
    </div>
  );
}
