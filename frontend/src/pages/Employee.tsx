import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { StaffApplication } from '../api/client';
import { Card, Button } from '../components/UI';

export const Employee = () => {
  const [apps, setApps] = useState<StaffApplication[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Модалка отказа
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Модалка успеха
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const load = () => api.getStaffApplications().then(setApps);

  useEffect(() => { load().finally(() => setLoading(false)); }, []);

  const change = async (id: number, status: string, reason?: string) => {
    try {
      await api.updateStatus(id, status, reason);
      // Показываем модалку успеха
      const messages: Record<string, string> = {
        approved: 'Заявка одобрена',
        rejected: 'Заявка отклонена',
        needs_info: 'Запрошены уточнения'
      };
      setSuccessMessage(messages[status] || 'Статус обновлен');
      load(); // Обновляем список
    } catch (e) {
      alert('Ошибка при смене статуса');
    }
  };

  const handleRejectSubmit = async () => {
    if (rejectingId && rejectReason.trim()) {
      await change(rejectingId, 'rejected', rejectReason.trim());
      setRejectingId(null);
      setRejectReason('');
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Загрузка...</div>;

  return (
    <div className="max-w-6xl mx-auto p-8 relative">
      <h1 className="text-3xl font-bold text-alfa-text mb-1">Кабинет сотрудника</h1>
      <p className="text-alfa-gray mb-8">Очередь заявок на рассмотрение</p>

      {/* Модалка отказа (ввод причины) */}
      {rejectingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <h3 className="text-xl font-bold mb-2">Отклонение заявки</h3>
            <p className="text-sm text-gray-500 mb-4">Клиент увидит эту причину в статусе заявки.</p>
            <textarea
              className="w-full p-3 border border-gray-300 rounded-lg mb-4 outline-none focus:border-alfa-red"
              rows={4}
              placeholder="Например: Недостаточная кредитная история..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setRejectingId(null)}>Отмена</Button>
              <Button onClick={handleRejectSubmit} disabled={!rejectReason.trim()}>Отклонить</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Модалка успеха */}
      {successMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-sm text-center">
            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">✓</div>
            <h3 className="text-xl font-bold mb-2">{successMessage}</h3>
            <p className="text-gray-500 mb-6">Клиент увидит обновленный статус в своем кабинете.</p>
            <Button className="w-full" onClick={() => setSuccessMessage(null)}>Понятно</Button>
          </Card>
        </div>
      )}

      <div className="space-y-4">
        {apps.map((app) => (
          <Card key={app.id} className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <p className="font-bold text-lg text-alfa-text">{app.company_name}</p>
                <span className="text-xs text-alfa-gray bg-gray-100 px-2 py-0.5 rounded">{app.owner_email}</span>
              </div>
              <p className="text-sm font-medium text-alfa-text mb-1">
                Заявка #{app.id} · {app.amount ? `${Number(app.amount).toLocaleString('ru-RU')} ₽` : '—'} · {app.term_months} мес.
              </p>
              <p className="text-sm text-alfa-gray">{app.purpose || '—'}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              {/* Кнопка "Открыть" ведет на результат, но без ссылки на профиль (см. Result.tsx) */}
              <Link to={`/result/${app.id}`}>
                <Button variant="secondary">Открыть</Button>
              </Link>
              
              <Button onClick={() => change(app.id, 'approved')} className="bg-green-600 hover:bg-green-700 text-white border-0">
                Одобрить
              </Button>
              <Button variant="secondary" onClick={() => change(app.id, 'needs_info')}>
                Запросить уточнения
              </Button>
              <Button variant="danger" onClick={() => setRejectingId(app.id)}>
                Отклонить
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};