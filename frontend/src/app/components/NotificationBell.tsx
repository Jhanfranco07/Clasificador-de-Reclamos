import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { Bell } from 'lucide-react';
import { Button } from './ui/button';
import { NotificationItem } from '../lib/api';
import { useNotifications } from '../lib/useNotifications';
import { useAuth } from '../contexts/AuthContext';

export default function NotificationBell() {
  const notifications = useNotifications();
  const { currentUser } = useAuth();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const outside = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, []);

  async function visit(item: NotificationItem) {
    try { await notifications.read(item.id); }
    catch { /* The persisted resource remains accessible when read tracking fails. */ }
    setOpen(false);
    if (item.orderId) {
      const root = currentUser?.role === 'MERCHANT' ? '/merchant/orders' : currentUser?.role === 'COURIER' ? '/courier/orders' : currentUser?.role === 'ADMIN' ? '/admin/orders' : '/orders';
      navigate(`${root}/${item.orderId}`);
    } else if (item.claimId) {
      navigate(`${currentUser?.role === 'CLIENT' ? '' : '/admin'}/claims/${item.claimId}`);
    } else {
      navigate(currentUser?.role === 'CLIENT' ? '/claims' : currentUser?.role === 'MERCHANT' ? '/merchant' : currentUser?.role === 'COURIER' ? '/courier' : '/admin/claims');
    }
  }

  return <div ref={container}>
    <Button type="button" variant="outline" size="icon" className="relative shrink-0 text-foreground bg-background"
      aria-label="Abrir notificaciones" aria-expanded={open}
      onClick={() => {
        if (!open) void notifications.refresh();
        setOpen(value => !value);
      }}>
      <Bell className="size-4" />
      {notifications.unread > 0 && <span className="absolute -right-1 -top-1 rounded-full bg-orange-500 px-1.5 text-[10px] text-white">{notifications.unread}</span>}
    </Button>
    {open && <section role="dialog" aria-label="Notificaciones"
      className="fixed right-4 top-20 z-[120] w-80 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-popover text-popover-foreground shadow-xl">
      <header className="border-b px-4 py-3">
        <h2 className="font-semibold">Notificaciones</h2>
        <p className="text-xs">{notifications.unread} aviso(s) sin leer</p>
      </header>
      {notifications.loading && <p role="status" className="p-3 text-sm">Actualizando notificaciones...</p>}
      {notifications.error && <div role="alert" className="p-3 text-sm">
        <p>{notifications.error}</p>
        <Button variant="outline" disabled={notifications.loading || notifications.busy} onClick={() => void notifications.refresh()}>Reintentar notificaciones</Button>
      </div>}
      {!notifications.loading && !notifications.error && notifications.items.length === 0 && <p className="p-4 text-sm">No tienes notificaciones.</p>}
      <div className="max-h-80 overflow-y-auto p-2">
        {notifications.items.map(item => <article key={item.id} className="rounded-md border-b p-3 break-words space-y-2">
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="text-xs">{item.message}</p>
          <p className="text-xs text-muted-foreground"><time>{item.createdAt}</time> · <span>{item.read ? 'Leída' : 'Sin leer'}</span></p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" disabled={notifications.busy} onClick={() => void visit(item)}>Ver {item.orderId ? 'pedido' : item.claimId ? 'reclamo' : 'detalle'}</Button>
            {!item.read && <Button size="sm" variant="outline" disabled={notifications.busy}
              aria-label={`Marcar notificación ${item.id} como leída`}
              onClick={() => void notifications.read(item.id).catch(() => undefined)}>Marcar como leída</Button>}
          </div>
        </article>)}
      </div>
      <footer className="border-t p-3 space-y-2">
        <p className="text-xs">Se muestran hasta 20 avisos, priorizando los no leídos.</p>
        <Button className="w-full" variant="outline" disabled={notifications.busy || !notifications.unread}
          onClick={() => void notifications.read().catch(() => undefined)}>Marcar todas como leídas</Button>
      </footer>
    </section>}
  </div>;
}
