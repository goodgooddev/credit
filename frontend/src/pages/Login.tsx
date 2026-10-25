import React, { useState } from 'react';
import { api } from '../api/client';
import { Card, Button } from '../components/UI';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

      const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await api.login({ email, password });
      
      if (user.role === 'staff') {
        window.location.href = '/employee';
      } else {
        window.location.href = '/profile';
      }
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-alfa-text">Вход в кабинет</h1>
          <p className="text-gray-500 text-sm mt-1">Управляйте финансами вашего бизнеса</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
              placeholder="ivan@romashka.ru"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
            <input
              type="password"
              required
              className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
              placeholder="••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </Button>
        </form>
        {/* хз добавим или нет
        <div className="mt-6 text-center text-sm text-gray-500">
          Нет аккаунта? <Link to="/register" className="text-alfa-red font-medium hover:underline">Зарегистрироваться</Link>
        </div> */}
      </Card>
    </div>
  );
};