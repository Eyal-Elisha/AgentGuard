import { useState, useEffect, useCallback } from 'react';
import { fetchBlacklistApi, updateBlacklistApi } from '../api/blacklistApi.js';

export function useBlacklist() {
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchBlacklist = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchBlacklistApi();
      setEntries(data.entries || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBlacklist();
  }, [fetchBlacklist]);

  const updateBlacklist = async (newEntries) => {
    try {
      setIsUpdating(true);
      setError(null);
      const data = await updateBlacklistApi(newEntries);
      setEntries(data.entries || []);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setIsUpdating(false);
    }
  };

  const addEntry = async (entry) => {
    const trimmed = entry.trim().toLowerCase();
    if (!trimmed || entries.includes(trimmed)) return false;
    return await updateBlacklist([...entries, trimmed]);
  };

  const removeEntry = async (entryToRemove) => {
    return await updateBlacklist(entries.filter(e => e !== entryToRemove));
  };

  return {
    entries, isLoading, isUpdating, error,
    addEntry, removeEntry, refresh: fetchBlacklist
  };
}
