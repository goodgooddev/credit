import { BrowserRouter, Routes, Route, Link, NavLink, Navigate } from 'react-router-dom';
import type { NavLinkRenderProps } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from './api/client';
import type { User } from './api/client';

// Импорт страниц
import { Catalog } from './pages/Catalog';
import { ApplicationForm } from './pages/ApplicationForm';
import { Result } from './pages/Result';
import { Employee } from './pages/Employee';
import { Profile } from './pages/Profile';
import { Login } from './pages/Login';

const navCls = ({ isActive }: NavLinkRenderProps) =>
  isActive
    ? 'text-alfa-red font-semibold bg-red-50 px-3 py-1.5 rounded-md transition-colors'
    : 'text-gray-600 hover:text-alfa-red px-3 py-1.5 rounded-md transition-colors';

// Защищенный роут
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    // getCurrentUser теперь синхронный метод, читающий localStorage
    setUser(api.getCurrentUser());
  }, []);

  if (user === undefined) return <div className="p-8 text-center text-gray-500">Загрузка...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

function App() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setUser(api.getCurrentUser());
  }, []);

  const handleLogout = () => {
    api.logout();
    setUser(null);
    window.location.href = '/login'; 
  };

  return (
    <BrowserRouter>
      <nav className="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm sticky top-0 z-10">
        <Link to="/" className="text-2xl font-black text-alfa-red tracking-tighter flex items-center gap-2">
          АЛЬФА <span className="text-alfa-text">КАБИНЕТ</span>
        </Link>
        <div className="flex gap-2 text-sm items-center">
          {/* Показываем Каталог только клиентам (или неавторизованным) */}
          {(!user || user.role === 'client') && (
            <NavLink to="/" end className={navCls}>Каталог</NavLink>
          )}

          {/* Сотруднику видно только сотрудникам */}
          {user?.role === 'staff' && (
            <NavLink to="/employee" className={navCls}>Сотруднику</NavLink>
          )}
          
          {user ? (
            <>
              {/* Профиль только для клиентов */}
              {user.role === 'client' && (
                <NavLink to="/profile" className={navCls}>Профиль</NavLink>
              )}
              <button onClick={handleLogout} className="text-gray-400 hover:text-red-500 ml-4 text-xs font-medium transition-colors">
                Выйти
              </button>
            </>
          ) : (
            <NavLink to="/login" className={navCls}>Вход</NavLink>
          )}
        </div>
      </nav>

      <main className="min-h-screen pb-12">
        <Routes>
          {/* Публичные страницы */}
          <Route path="/" element={<Catalog />} />
          <Route path="/login" element={<Login />} />

          {/* Защищенные страницы (только для авторизованных) */}
          <Route path="/profile" element={
            <ProtectedRoute><Profile /></ProtectedRoute>
          } />
          {/* Кабинет сотрудника защищен (но проверку роли лучше делать внутри Employee) */}
          // В Routes
          <Route path="/employee" element={
            <ProtectedRoute>
              <Employee />
            </ProtectedRoute>
          } />
          <Route path="/application/new" element={
            <ProtectedRoute><ApplicationForm /></ProtectedRoute>
          } />
          <Route path="/result/:id" element={
            <ProtectedRoute><Result /></ProtectedRoute>
          } />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;