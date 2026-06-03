import { Link, useNavigate, useLocation } from 'react-router';
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
import { Package, Home, ShoppingBag, AlertCircle, HelpCircle, LogOut, User, Bell } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { listNotifications, markNotificationsRead, NotificationItem } from '../lib/api';

interface ClientLayoutProps {
  children: ReactNode;
}

export default function ClientLayout({ children }: ClientLayoutProps) {
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
    { path: '/dashboard', label: 'Inicio', icon: Home },
    { path: '/orders', label: 'Mis pedidos', icon: ShoppingBag },
    { path: '/claims', label: 'Mis reclamos', icon: AlertCircle },
    { path: '/help', label: 'Ayuda', icon: HelpCircle },
  ];

  const isActive = (path: string) => location.pathname === path;

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
                <div className="absolute right-0 top-11 z-[100] w-80 overflow-hidden rounded-lg border bg-white shadow-xl">
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
                <Button variant="ghost" className="relative size-10 rounded-full">
                  <Avatar>
                    <AvatarFallback>
                      {currentUser?.name?.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Mi cuenta</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <User className="mr-2 size-4" />
                  Perfil
                </DropdownMenuItem>
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
              <Link key={item.path} to={item.path}>
                <Button
                  variant={isActive(item.path) ? 'default' : 'ghost'}
                  className="gap-2"
                >
                  <item.icon className="size-4" />
                  {item.label}
                </Button>
              </Link>
            ))}
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
}
