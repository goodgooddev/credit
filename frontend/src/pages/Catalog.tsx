import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Product } from '../api/client';
import { Card, Button } from '../components/UI';

export const Catalog = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getProducts()
      .then(setProducts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-center">Загрузка...</div>;

  return (
    <div className="max-w-6xl mx-auto p-8">
      <h1 className="text-3xl font-bold text-alfa-text mb-8">Кредитные продукты</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {products.map(p => (
          <Card key={p.id} className="flex flex-col">
            <h3 className="text-xl font-bold mb-2">{p.name}</h3>
            <p className="text-gray-500 mb-4 flex-1">{p.description}</p>
            <div className="text-sm text-gray-600 mb-1">
              Сумма: {Number(p.min_amount).toLocaleString('ru-RU')} – {Number(p.max_amount).toLocaleString('ru-RU')} ₽
            </div>
            <div className="text-sm text-gray-600 mb-1">
              Срок: {p.min_term_months} – {p.max_term_months} мес.
            </div>
            <div className="text-2xl font-bold text-alfa-red mb-4 mt-2">
              от {Number(p.annual_rate)}%
            </div>
            <Button onClick={() => navigate(`/application/new?product=${p.id}`)}>
              Оформить
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
};