import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ApplicationDetail, Event, User } from '../api/client';
import { Card, Button } from '../components/UI';

const STATUS_MAP: Record<string, { text: string; cls: string }> = {
  draft: { text: 'Черновик', cls: 'text-gray-500' },
  submitted: { text: 'На рассмотрении', cls: 'text-yellow-600' },
  needs_info: { text: 'Требуются уточнения', cls: 'text-orange-600' },
  approved: { text: 'Одобрено', cls: 'text-green-600' },
  rejected: { text: 'Отказано', cls: 'text-red-600' },
  counter_offer: { text: 'Встречное предложение', cls: 'text-blue-600' },
  accepted: { text: 'Принято', cls: 'text-green-700' },
};

export const Result = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [app, setApp] = useState<ApplicationDetail | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(api.getCurrentUser());
    if (!id) return;
    
    Promise.all([api.getApplication(Number(id)), api.getApplicationEvents(Number(id))])
      .then(([a, e]) => { setApp(a); setEvents(e); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-center text-gray-500">Загрузка...</div>;
  if (!app) return <div className="p-8 text-center text-red-500">Заявка не найдена</div>;

  const status = STATUS_MAP[app.status] || { text: app.status, cls: 'text-gray-500' };

  return (
    <div className="max-w-2xl mx-auto p-8 space-y-6">
      {/* Навигация назад в зависимости от роли */}
      {user?.role === 'staff' ? (
        <Link to="/employee" className="text-sm text-gray-500 hover:text-alfa-red inline-block mb-2">
          ← Назад к списку заявок
        </Link>
      ) : (
        <Link to="/profile" className="text-sm text-gray-500 hover:text-alfa-red inline-block mb-2">
          ← Назад в профиль
        </Link>
      )}
      
      <Card className="text-center">
        <p className="text-sm text-gray-500 uppercase mb-2">Заявка #{app.id}</p>
        <h1 className="text-2xl font-bold mb-2">{app.product?.name || 'Кредитный продукт'}</h1>
        <p className="text-gray-500 mb-6">
          {app.amount ? `${Number(app.amount).toLocaleString('ru-RU')} ₽` : '—'} · {app.term_months} мес.
        </p>
        <p className={`text-3xl font-bold ${status.cls}`}>{status.text}</p>
      </Card>

      {/* 1. Блок ОДОБРЕНИЯ */}
      {app.status === 'approved' && (
        <Card className="bg-green-50 border-green-200">
          <h3 className="text-lg font-bold text-green-800 mb-2">Поздравляем!</h3>
          <p className="text-green-700 mb-4">
            Ваша заявка одобрена. Следующий шаг — подписание договора и получение средств.
          </p>
          <Button className="w-full">Подписать договор</Button>
        </Card>
      )}

      {/* 2. Блок ОТКАЗА */}
      {app.status === 'rejected' && (
        <Card className="bg-red-50 border-red-200">
          <h3 className="text-lg font-bold text-red-800 mb-2">К сожалению, заявка отклонена</h3>
          <p className="text-red-700 mb-4">
            {app.decision ? `Причина: ${app.decision}` : 'Банк принял решение об отказе без указания причины.'}
          </p>
          <Link to="/">
            <Button variant="secondary" className="w-full">Выбрать другой продукт</Button>
          </Link>
        </Card>
      )}

      {/* 3. Блок ЗАПРОСА УТОЧНЕНИЙ */}
      {app.status === 'needs_info' && (
        <Card className="bg-orange-50 border-orange-200">
          <h3 className="text-lg font-bold text-orange-800 mb-2">Требуются уточнения</h3>
          <p className="text-orange-700 mb-4">
            Банку не хватает информации для принятия решения. Пожалуйста, дополните заявку.
          </p>
          <Button 
            className="w-full" 
            onClick={() => navigate(`/application/new?product=${app.product_id}&draft=${app.id}`)}
          >
            Дополнить заявку
          </Button>
        </Card>
      )}

      {/* Информация о заявке (для всех статусов) */}
      <Card>
        <h3 className="font-bold mb-4">Детали заявки</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Компания:</span>
            <span className="font-medium">{app.company?.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Цель:</span>
            <span className="font-medium">{app.purpose || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Дата подачи:</span>
            <span className="font-medium">
              {app.submitted_at ? new Date(app.submitted_at).toLocaleDateString('ru-RU') : '—'}
            </span>
          </div>
        </div>
      </Card>

      {/* История событий */}
      <Card>
        <h3 className="font-bold mb-4">История событий</h3>
        {events.length === 0 ? (
          <p className="text-sm text-gray-500">История пока пуста</p>
        ) : (
          <div className="space-y-4 border-l-2 border-gray-200 pl-4">
            {events.map(e => (
              <div key={e.id} className="relative">
                <div className="absolute -left-[21px] top-1.5 w-2 h-2 bg-alfa-red rounded-full" />
                <p className="text-sm font-medium">{e.event_type}</p>
                <p className="text-xs text-gray-400">{new Date(e.created_at).toLocaleString('ru-RU')}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};