import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User } from '../types';
import { clearStoredToken, getMe, getStoredToken, loginUser, registerUser } from '../lib/api';

interface AuthContextType {
  currentUser: User | null;
  login: (email: string, password: string) => Promise<User | null>;
  register: (payload: { name: string; email: string; phone?: string; password: string }) => Promise<User | null>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const toUser = (user: {
  id: string;
  name: string;
  email: string;
  role: 'CLIENT' | 'AGENT' | 'ADMIN';
  phone?: string;
  createdAt: string;
}): User => ({
  id: user.id,
  name: user.name,
  email: user.email,
  role: user.role,
  phone: user.phone,
  createdAt: new Date(user.createdAt),
});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    getMe()
      .then((result) => setCurrentUser(toUser(result.user)))
      .catch(() => {
        clearStoredToken();
        setCurrentUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearStoredToken();
      setCurrentUser(null);
    };
    window.addEventListener('smartclaim:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('smartclaim:unauthorized', handleUnauthorized);
  }, []);

  const login = async (email: string, password: string): Promise<User | null> => {
    try {
      const result = await loginUser(email, password);
      const user = toUser(result.user);
      setCurrentUser(user);
      return user;
    } catch {
      return null;
    }
  };

  const register = async (payload: { name: string; email: string; phone?: string; password: string }): Promise<User | null> => {
    try {
      const result = await registerUser(payload);
      const user = toUser(result.user);
      setCurrentUser(user);
      return user;
    } catch {
      return null;
    }
  };

  const logout = () => {
    clearStoredToken();
    setCurrentUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        login,
        register,
        logout,
        isAuthenticated: !!currentUser,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
