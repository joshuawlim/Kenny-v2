import { useEffect, useCallback } from 'react';

type KeyboardShortcut = string;
type Handler = (event?: KeyboardEvent) => void;

// Parse shortcut string into key components
function parseShortcut(shortcut: string) {
  const parts = shortcut.toLowerCase().split('+');
  const modifiers = {
    cmd: false,
    ctrl: false,
    alt: false,
    shift: false,
  };
  let key = '';

  parts.forEach(part => {
    switch (part) {
      case 'cmd':
      case 'meta':
        modifiers.cmd = true;
        break;
      case 'ctrl':
        modifiers.ctrl = true;
        break;
      case 'alt':
      case 'option':
        modifiers.alt = true;
        break;
      case 'shift':
        modifiers.shift = true;
        break;
      case 'enter':
        key = 'Enter';
        break;
      case 'escape':
      case 'esc':
        key = 'Escape';
        break;
      case 'up':
        key = 'ArrowUp';
        break;
      case 'down':
        key = 'ArrowDown';
        break;
      case 'left':
        key = 'ArrowLeft';
        break;
      case 'right':
        key = 'ArrowRight';
        break;
      default:
        key = part.toUpperCase();
    }
  });

  return { modifiers, key };
}

// Check if event matches shortcut
function matchesShortcut(event: KeyboardEvent, shortcut: string) {
  const { modifiers, key } = parseShortcut(shortcut);
  
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const cmdKey = isMac ? event.metaKey : event.ctrlKey;
  
  return (
    (modifiers.cmd ? cmdKey : !cmdKey) &&
    (modifiers.ctrl ? event.ctrlKey : !event.ctrlKey) &&
    (modifiers.alt ? event.altKey : !event.altKey) &&
    (modifiers.shift ? event.shiftKey : !event.shiftKey) &&
    event.key.toUpperCase() === key
  );
}

export function useKeyboard(
  shortcut: KeyboardShortcut,
  handler: Handler,
  enabled = true
) {
  const memoizedHandler = useCallback(handler, []);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger in input fields unless explicitly allowed
      const target = event.target as HTMLElement;
      const isInput = ['INPUT', 'TEXTAREA'].includes(target.tagName);
      
      if (isInput && !shortcut.includes('cmd') && !shortcut.includes('ctrl')) {
        return;
      }

      if (matchesShortcut(event, shortcut)) {
        event.preventDefault();
        memoizedHandler(event);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcut, memoizedHandler, enabled]);
}

// Multiple keyboard shortcuts
export function useKeyboardShortcuts(
  shortcuts: Record<KeyboardShortcut, Handler>,
  enabled = true
) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const isInput = ['INPUT', 'TEXTAREA'].includes(target.tagName);

      for (const [shortcut, handler] of Object.entries(shortcuts)) {
        if (isInput && !shortcut.includes('cmd') && !shortcut.includes('ctrl')) {
          continue;
        }

        if (matchesShortcut(event, shortcut)) {
          event.preventDefault();
          handler(event);
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, enabled]);
}

// Common shortcuts
export const commonShortcuts = {
  newChat: 'cmd+n',
  search: 'cmd+k',
  send: 'cmd+enter',
  stop: 'escape',
  editLast: 'alt+up',
  nextModel: 'cmd+]',
  prevModel: 'cmd+[',
  focusLeft: 'alt+left',
  focusRight: 'alt+right',
  toggleTheme: 'cmd+shift+l',
  settings: 'cmd+,',
};