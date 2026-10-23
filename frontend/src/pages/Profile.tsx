import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { User, Application, Company } from '../api/client';
import { Card, Button } from '../components/UI';

const STATUS_MAP: Record<string, { text: string; cls: string }> = {
  draft: { text: 'Черновик', cls: 'bg-gray-100 text-gray-600' },
  submitted: { text: 'На рассмотрении', cls: 'bg-yellow-100 text-yellow-700' },
  needs_info: { text: 'Нужна информация', cls: 'bg-orange-100 text-orange-700' },
  approved: { text: 'Одобрено', cls: 'bg-green-100 text-green-700' },
  rejected: { text: 'Отказано', cls: 'bg-red-100 text-red-700' },
  counter_offer: { text: 'Встречное предложение', cls: 'bg-blue-100 text-blue-700' },
  accepted: { text: 'Принято', cls: 'bg-green-100 text-green-700' },
};

export const Profile = () => {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      Promise.resolve(api.getCurrentUser()),
      api.getApplications().catch(() => []),
      api.getCompanies().catch(() => []),
    ])
      .then(([u, a, c]) => {
        setUser(u);
        setApps(a);
        setCompany(c[0] || null);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => {
    api.logout();
    navigate('/login');
    window.location.reload();
  };

  if (loading) return <div className="p-6 text-center text-gray-500">Загрузка профиля...</div>;
  if (!user) return <div className="p-6 text-center">Не авторизован</div>;

  return (
    <div className="max-w-6xl mx-auto p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
      <Card className="h-fit">
        <div className="w-20 h-20 rounded-full bg-red-100 text-alfa-red flex items-center justify-center text-2xl font-bold mb-5 mx-auto">
          {user.full_name.split(' ').map((s) => s[0]).slice(0, 2).join('')}
        </div>
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-alfa-text">{user.full_name}</h2>
          <p className="text-alfa-gray text-sm capitalize">{user.role}</p>
        </div>

        {company && (
          <div className="space-y-3 text-sm border-t border-gray-100 pt-5">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Компания</span>
              <span className="font-medium text-alfa-text text-right">{company.name}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">ИНН</span>
              <span className="font-mono text-alfa-text bg-gray-50 px-2 py-0.5 rounded">{company.inn}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Сотрудников</span>
              <span className="text-alfa-text">{company.employees_count}</span>
            </div>
          </div>
        )}

        <div className="mt-6 pt-6 border-t border-gray-100">
          <Button variant="danger" className="w-full" onClick={handleLogout}>
            Выйти из аккаунта
          </Button>
        </div>
      </Card>

      <div className="lg:col-span-2">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-alfa-text">Мои заявки</h1>
          <Link to="/" className="text-sm font-medium text-alfa-red hover:underline bg-red-50 px-4 py-2 rounded-lg">
            + Новая заявка
          </Link>
        </div>

        {apps.length === 0 ? (
          <Card><p className="text-gray-500">Заявок пока нет.</p></Card>
        ) : (
          <div className="space-y-4">
            {apps.map((app) => {
              const st = STATUS_MAP[app.status] || { text: app.status, cls: 'bg-gray-100 text-gray-600' };
              const isEditable = app.status === 'draft' || app.status === 'needs_info';
              const linkTo = isEditable
                ? `/application/new?product=${app.product_id}&draft=${app.id}`
                : `/result/${app.id}`;

              return (
                <Link key={app.id} to={linkTo} className="block">
                  <Card className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-alfa-red/30 hover:shadow-md transition-all cursor-pointer">
                    <div>
                      <p className="font-bold text-lg text-alfa-text mb-1">
                        Заявка #{app.id} <span className="text-gray-400 font-normal text-sm">· продукт {app.product_id}</span>
                      </p>
                      <p className="text-sm text-alfa-gray">
                        {app.amount ? `${Number(app.amount).toLocaleString('ru-RU')} ₽` : '—'} · {app.term_months ?? '—'} мес. ·{' '}
                        {new Date(app.created_at).toLocaleDateString('ru-RU')}
                      </p>
                      <p className="text-sm text-gray-400 mt-1">{app.purpose || '—'}</p>
                    </div>
                    <span className={`text-xs font-semibold px-3 py-1.5 rounded-full whitespace-nowrap ${st.cls}`}>
                      {st.text}
                    </span>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};