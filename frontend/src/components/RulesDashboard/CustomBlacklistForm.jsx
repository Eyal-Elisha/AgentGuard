import { useState } from 'react';
import './CustomBlacklistForm.css';

export default function CustomBlacklistForm({ onAdd, isLoading, isUpdating }) {
  const [newDomain, setNewDomain] = useState('');

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newDomain.trim()) return;
    
    const success = await onAdd(newDomain);
    if (success) {
      setNewDomain('');
    }
  };

  return (
    <form onSubmit={handleAdd} className="custom-blacklist-input-group">
      <input
        type="text"
        className="custom-blacklist-input"
        placeholder="e.g., tracking.example.com or example.com/analytics"
        value={newDomain}
        onChange={(e) => setNewDomain(e.target.value)}
        disabled={isLoading || isUpdating}
      />
      <button 
        type="submit" 
        className="custom-blacklist-add-btn"
        disabled={!newDomain.trim() || isLoading || isUpdating}
      >
        {isUpdating ? 'Adding...' : 'Add Domain'}
      </button>
    </form>
  );
}
