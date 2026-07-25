import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';

const STORAGE_KEY = 'agentguard-theme';

function readDomTheme() {
  if (typeof document === 'undefined') return 'dark';
  const fromDom = document.documentElement.getAttribute('data-theme');
  if (fromDom === 'light' || fromDom === 'dark') return fromDom;
  return 'dark';
}

function applyTheme(next) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', next);
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    /* ignore */
  }
}

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readDomTheme);

  const setTheme = useCallback((next) => {
    const value = next === 'light' ? 'light' : 'dark';
    applyTheme(value);
    setThemeState(value);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      applyTheme(next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (ctx == null) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}
