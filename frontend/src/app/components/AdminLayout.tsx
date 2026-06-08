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
import {
  LayoutDashboard,
  Inbox,
  FileText,
  Settings,
  BarChart3,
  LogOut,
  Package,
  UserRound,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';
import ThemeToggle from './ThemeToggle';

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navItems = [
    { path: '/admin', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/admin/claims', label: 'Bandeja de reclamos', icon: Inbox },
    ...(currentUser?.role === 'ADMIN'
      ? [
          { path: '/admin/knowledge', label: 'Base documental', icon: FileText },
          { path: '/admin/ai-config', label: 'Configuración IA', icon: Settings },
          { path: '/admin/reports', label: 'Reportes', icon: BarChart3 },
        ]
      : []),
  ];

  const isActive = (path: string) => {
    if (path === '/admin') {
      return location.pathname === '/admin';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-slate-950 text-white dark:bg-slate-900 border-b border-slate-800 dark:border-slate-700 sticky top-0 z-50 shadow-lg shadow-slate-950/10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/admin" className="flex items-center gap-2">
            <span className="flex size-10 items-center justify-center rounded-xl bg-orange-500 text-white">
              <Package className="size-6" />
            </span>
            <div>
              <span className="font-bold text-xl">SmartClaim AI</span>
              <span className="text-xs text-gray-400 block">
                {currentUser?.role === 'ADMIN' ? 'Panel Administrativo' : 'Panel de Soporte'}
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-2 sm:gap-4">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="h-11 gap-3 rounded-lg px-2 text-white hover:bg-slate-800 hover:text-white sm:px-3"
                  aria-label="Abrir menú de cuenta"
                >
                  <span className="hidden text-right sm:block">
                    <span className="block text-xs text-gray-400">
                      {currentUser?.role === 'ADMIN' ? 'Administrador' : 'Agente'}
                    </span>
                    <span className="block max-w-36 truncate text-sm font-medium">
                      {currentUser?.name}
                    </span>
                  </span>
                  <Avatar className="size-9">
                    <AvatarFallback className="bg-orange-600">
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
                <DropdownMenuItem onClick={() => navigate('/admin/profile')}>
                  <UserRound className="mr-2 size-4" />
                  Editar perfil
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

      <nav className="bg-card border-b border-border shadow-sm">
        <div className="container mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto">
            {navItems.map((item) => (
              <Button
                key={item.path}
                asChild
                  variant={isActive(item.path) ? 'default' : 'ghost'}
                  className={isActive(item.path) ? 'gap-2 whitespace-nowrap bg-orange-500 text-white hover:bg-orange-600' : 'gap-2 whitespace-nowrap'}
              >
                <Link to={item.path} aria-current={isActive(item.path) ? 'page' : undefined}>
                  <item.icon className="size-4" />
                  {item.label}
                </Link>
              </Button>
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

