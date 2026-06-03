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
import { ReactNode, useEffect, useState } from 'react';
import { listNotifications, markNotificationsRead, NotificationItem } from '../lib/api';

interface ClientLayoutProps {
  children: ReactNode;
}

export default function ClientLayout({ children }: ClientLayoutProps) {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const unread = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    if (currentUser?.role !== 'CLIENT') return;
    listNotifications()
      .then((result) => setNotifications(result.items))
      .catch(() => setNotifications([]));
  }, [currentUser?.role]);

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
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="relative">
                  <Bell className="size-4" />
                  {unread > 0 && (
                    <span className="absolute -right-1 -top-1 rounded-full bg-orange-500 px-1.5 text-[10px] text-white">
                      {unread}
                    </span>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80">
                <DropdownMenuLabel>Notificaciones</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {notifications.length === 0 ? (
                  <DropdownMenuItem disabled>No tienes avisos pendientes</DropdownMenuItem>
                ) : (
                  notifications.slice(0, 5).map((item) => (
                    <DropdownMenuItem key={item.id} asChild>
                      <Link
                        to={item.claimId ? `/claims/${item.claimId}` : '/claims'}
                        onClick={async () => {
                          try {
                            const result = await markNotificationsRead();
                            setNotifications(result.items);
                          } catch {
                            // Navigation should still work even if the read flag fails.
                          }
                        }}
                        className="flex cursor-pointer flex-col items-start gap-1"
                      >
                        <span className="font-semibold">{item.title}</span>
                        <span className="text-xs text-gray-500">{item.message}</span>
                        <span className="text-xs font-medium text-orange-600">Ver reclamo</span>
                      </Link>
                    </DropdownMenuItem>
                  ))
                )}
                {notifications.length > 0 && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={async () => {
                        const result = await markNotificationsRead();
                        setNotifications(result.items);
                      }}
                    >
                      Marcar como leidas
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
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
