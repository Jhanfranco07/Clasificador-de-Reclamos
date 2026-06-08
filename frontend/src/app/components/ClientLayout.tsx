import { Link, Outlet, useNavigate, useLocation } from 'react-router';
import { Button } from './ui/button';
import { Avatar, AvatarFallback } from './ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Package, Home, ShoppingBag, AlertCircle, HelpCircle, LogOut, Bell, Utensils, ShoppingCart } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { createContext, ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { listNotifications, markNotificationsRead, NotificationItem } from '../lib/api';

interface ClientLayoutProps {
  children?: ReactNode;
}

const ClientLayoutContext = createContext(false);

export default function ClientLayout({ children }: ClientLayoutProps) {
  const insideClientLayout = useContext(ClientLayoutContext);
  if (insideClientLayout) {
    return <>{children}</>;
  }
  return <ClientLayoutShell>{children}</ClientLayoutShell>;
}

function ClientLayoutShell({ children }: ClientLayoutProps) {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement | null>(null);
  const unread = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    if (currentUser?.role !== 'CLIENT') return;
    listNotifications()
      .then((result) => setNotifications(result.items))
      .catch(() => setNotifications([]));
  }, [currentUser?.role]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!notificationsRef.current?.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navItems = [
    { path: '/dashboard', label: 'Inicio', icon: Home, matches: ['/dashboard'] },
    { path: '/restaurants', label: 'Restaurantes', icon: Utensils, matches: ['/restaurants', '/products'] },
    { path: '/cart', label: 'Carrito', icon: ShoppingCart, matches: ['/cart', '/checkout'] },
    { path: '/orders', label: 'Mis pedidos', icon: ShoppingBag, matches: ['/orders'] },
    { path: '/claims', label: 'Mis reclamos', icon: AlertCircle, matches: ['/claims', '/notifications'] },
    { path: '/help', label: 'Ayuda', icon: HelpCircle, matches: ['/help'] },
  ];

  const isActive = (matches: string[]) => matches.some((path) => (
    location.pathname === path || (path !== '/dashboard' && location.pathname.startsWith(`${path}/`))
  ));

  const isCatalogView = ['/restaurants', '/products', '/cart'].some(
    (path) => location.pathname === path || location.pathname.startsWith(`${path}/`)
  );

  const openNotification = async (item: NotificationItem) => {
    setNotificationsOpen(false);
    try {
      const result = await markNotificationsRead();
      setNotifications(result.items);
    } catch {
      // The user should still be able to open the claim if read tracking fails.
    }
    navigate(item.claimId ? `/claims/${item.claimId}` : '/claims');
  };

  return (
    <ClientLayoutContext.Provider value>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <Package className="size-8 text-orange-500" />
            <span className="font-bold text-xl">SmartClaim AI</span>
          </Link>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600 hidden md:block">
              Hola, {currentUser?.name?.split(' ')[0]}
            </span>
            <div className="relative" ref={notificationsRef}>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="relative"
                aria-label="Abrir notificaciones"
                aria-expanded={notificationsOpen}
                onClick={() => setNotificationsOpen((open) => !open)}
              >
                <Bell className="size-4" />
                {unread > 0 && (
                  <span className="absolute -right-1 -top-1 rounded-full bg-orange-500 px-1.5 text-[10px] text-white">
                    {unread}
                  </span>
                )}
              </Button>

              {notificationsOpen && (
                <div
                  className="absolute right-0 top-11 z-[100] w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border bg-white shadow-xl"
                  role="dialog"
                  aria-label="Notificaciones"
                >
                  <div className="border-b px-4 py-3">
                    <p className="font-semibold">Notificaciones</p>
                    <p className="text-xs text-gray-500">
                      {unread > 0 ? `${unread} aviso(s) sin leer` : 'Sin avisos pendientes'}
                    </p>
                  </div>

                  <div className="max-h-80 overflow-y-auto p-2">
                    {notifications.length === 0 ? (
                      <div className="rounded-md px-3 py-4 text-sm text-gray-500">
                        No tienes avisos pendientes.
                      </div>
                    ) : (
                      notifications.slice(0, 8).map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => openNotification(item)}
                          className="w-full rounded-md px-3 py-2 text-left hover:bg-gray-50"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-sm font-semibold">{item.title}</span>
                            {!item.read && <span className="mt-1 size-2 rounded-full bg-orange-500" />}
                          </div>
                          <p className="mt-1 text-xs text-gray-500">{item.message}</p>
                          <p className="mt-1 text-xs font-medium text-orange-600">Ver reclamo</p>
                        </button>
                      ))
                    )}
                  </div>

                  {notifications.length > 0 && (
                    <button
                      type="button"
                      onClick={async () => {
                        const result = await markNotificationsRead();
                        setNotifications(result.items);
                        setNotificationsOpen(false);
                      }}
                      className="w-full border-t px-4 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Marcar como leídas
                    </button>
                  )}
                </div>
              )}
            </div>
            <Button variant="outline" size="sm" className="hidden sm:flex gap-2" onClick={handleLogout}>
              <LogOut className="size-4" />
              Salir
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative size-10 rounded-full" aria-label="Abrir menú de cuenta">
                  <Avatar>
                    <AvatarFallback>
                      {currentUser?.name?.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Mi cuenta</DropdownMenuLabel>
                <div className="px-2 pb-2 text-xs text-gray-500">
                  <p className="font-medium text-gray-700">{currentUser?.name}</p>
                  <p className="truncate">{currentUser?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 size-4" />
                  Cerrar sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b">
        <div className="container mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto">
            {navItems.map((item) => (
              <Button
                key={item.path}
                asChild
                  variant={isActive(item.matches) ? 'default' : 'ghost'}
                  className="gap-2 whitespace-nowrap"
              >
                <Link to={item.path} aria-current={isActive(item.matches) ? 'page' : undefined}>
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              </Button>
            ))}
          </div>
        </div>
      </nav>

      <main className={isCatalogView ? 'w-full' : 'container mx-auto px-4 py-8'}>
        {children ?? <Outlet />}
      </main>
    </div>
    </ClientLayoutContext.Provider>
  );
}
