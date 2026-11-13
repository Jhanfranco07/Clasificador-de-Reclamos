import { Link, Outlet, useNavigate, useLocation } from 'react-router';
import { Button } from './ui/button';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Package, Home, ShoppingBag, AlertCircle, HelpCircle, LogOut, Utensils, ShoppingCart, UserRound } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { createContext, ReactNode, useContext, useEffect, useRef, useState } from 'react';
import NotificationBell from './NotificationBell';
import ThemeToggle from './ThemeToggle';

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
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!accountRef.current?.contains(event.target as Node)) {
        setAccountOpen(false);
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

  return (
    <ClientLayoutContext.Provider value>
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-card border-b border-border sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <Package className="size-8 text-orange-500" />
            <span className="sr-only sm:not-sr-only font-bold text-xl">SmartClaim AI</span>
          </Link>

          <div className="flex items-center gap-2 sm:gap-4">
            <ThemeToggle />
            <NotificationBell />
            <div className="relative" ref={accountRef}>
              <Button
                type="button"
                variant="ghost"
                className="h-11 gap-3 rounded-lg px-2 sm:px-3"
                aria-label="Abrir menú de cuenta"
                aria-expanded={accountOpen}
                onClick={() => setAccountOpen((open) => !open)}
              >
                <span className="hidden text-left sm:block">
                  <span className="block text-xs text-muted-foreground">Mi cuenta</span>
                  <span className="block max-w-32 truncate text-sm font-medium">
                    {currentUser?.name?.split(' ')[0]}
                  </span>
                </span>
                <Avatar className="size-9">
                  <AvatarFallback>
                    {currentUser?.name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </Button>

              {accountOpen && (
                <div className="absolute right-0 top-12 z-[110] w-64 overflow-hidden rounded-lg border border-border bg-popover text-popover-foreground shadow-xl">
                  <div className="border-b border-border px-4 py-3">
                    <p className="text-sm font-semibold">{currentUser?.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{currentUser?.email}</p>
                  </div>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm hover:bg-accent"
                    onClick={() => {
                      setAccountOpen(false);
                      navigate('/profile');
                    }}
                  >
                  <UserRound className="mr-2 size-4" />
                  Editar perfil
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 border-t border-border px-4 py-3 text-left text-sm hover:bg-accent"
                    onClick={handleLogout}
                  >
                  <LogOut className="mr-2 size-4" />
                  Cerrar sesión
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-card border-b border-border">
        <div className="container mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto">
            {navItems.map((item) => (
              <Button
                key={item.path}
                asChild
                  variant={isActive(item.matches) ? 'default' : 'ghost'}
                  className={isActive(item.matches) ? 'gap-2 whitespace-nowrap bg-orange-500 text-white hover:bg-orange-600' : 'gap-2 whitespace-nowrap'}
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
