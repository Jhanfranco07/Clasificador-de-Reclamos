import { useCallback, useEffect, useRef, useState } from 'react';
import { listNotifications, markNotificationsRead, markNotificationRead, NotificationItem } from './api';
import { useAuth } from '../contexts/AuthContext';

export function useNotifications() {
  const { currentUser } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const inFlight = useRef<Promise<void> | null>(null);
  const mutating = useRef(false);

  const refresh = useCallback(() => {
    if (!currentUser || mutating.current) return Promise.resolve();
    if (inFlight.current) return inFlight.current;
    const epoch = generation.current;
    setLoading(true);
    const task = listNotifications().then(result => {
      if (epoch !== generation.current) return;
      setItems(result.items);
      setUnread(result.unread);
      setError('');
    }).catch(err => {
      if (epoch === generation.current) {
        setError(err instanceof Error ? err.message : 'No se pudieron cargar las notificaciones.');
      }
    }).finally(() => {
      if (epoch === generation.current) setLoading(false);
      if (inFlight.current === task) inFlight.current = null;
    });
    inFlight.current = task;
    return task;
  }, [currentUser?.id, currentUser?.role]);

  useEffect(() => {
    generation.current += 1;
    inFlight.current = null;
    mutating.current = false;
    setBusy(false);
    setLoading(false);
    setItems([]);
    setUnread(0);
    setError('');
    void refresh();
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refresh();
    };
    const interval = window.setInterval(onVisible, 30_000);
    window.addEventListener('focus', onVisible);
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('smartclaim:notifications-changed', onVisible);
    return () => {
      generation.current += 1;
      window.clearInterval(interval);
      window.removeEventListener('focus', onVisible);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('smartclaim:notifications-changed', onVisible);
    };
  }, [refresh]);

  async function read(id?: string) {
    if (mutating.current) return;
    mutating.current = true;
    setBusy(true);
    const epoch = generation.current;
    try {
      await inFlight.current;
      if (epoch !== generation.current) return;
      const result = id ? await markNotificationRead(id) : await markNotificationsRead();
      if (epoch !== generation.current) return;
      setItems(result.items);
      setUnread(result.unread);
      setError('');
    } catch (err) {
      if (epoch === generation.current) {
        setError(err instanceof Error ? err.message : 'No se pudo actualizar la lectura.');
      }
      throw err;
    } finally {
      if (epoch === generation.current) {
        mutating.current = false;
        setBusy(false);
      }
    }
  }

  return { items, unread, loading, busy, error, refresh, read };
}
