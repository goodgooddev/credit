import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Product, Company } from '../api/client';
import { Card, Button } from '../components/UI';

export const ApplicationForm = () => {
  const [params] = useSearchParams();
  const productId = Number(params.get('product'));
  const draftId = params.get('draft') ? Number(params.get('draft')) : null;

  const [product, setProduct] = useState<Product | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  
  // Поля формы
  const [amount, setAmount] = useState('');
  const [term, setTerm] = useState('');
  const [purpose, setPurpose] = useState('');
  // Новые поля для скоринга
  const [annualRevenue, setAnnualRevenue] = useState('');
  const [monthlyExpenses, setMonthlyExpenses] = useState('');
  const [existingDebt, setExistingDebt] = useState('0');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [appId, setAppId] = useState<number | null>(draftId);
  const [showSuccess, setShowSuccess] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    const init = async () => {
      try {
        const [prods, comps] = await Promise.all([api.getProducts(), api.getCompanies()]);
        const p = prods.find(x => x.id === productId);
        if (!p) throw new Error('Продукт не найден');
        setProduct(p);
        setCompanies(comps);

        if (draftId) {
          const draft = await api.getApplication(draftId);
          setAmount(draft.amount || '');
          setTerm(draft.term_months ? String(draft.term_months) : '');
          setPurpose(draft.purpose || '');
          setAnnualRevenue(draft.annual_revenue || '');
          setMonthlyExpenses(draft.monthly_expenses || '');
          setExistingDebt(draft.existing_debt || '0');
        } else {
          setAmount(p.min_amount);
          setTerm(String(p.min_term_months));
        }
      } catch (e: any) {
        setErrors({ global: e.message });
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [productId, draftId]);

  const validate = () => {
    const errs: Record<string, string> = {};
    const numAmount = Number(amount);
    const numTerm = Number(term);

    if (!amount || isNaN(numAmount)) errs.amount = 'Введите сумму';
    else if (product && (numAmount < Number(product.min_amount) || numAmount > Number(product.max_amount))) 
      errs.amount = `От ${Number(product.min_amount).toLocaleString()} до ${Number(product.max_amount).toLocaleString()}`;

    if (!term || isNaN(numTerm)) errs.term = 'Введите срок';
    else if (product && (numTerm < product.min_term_months || numTerm > product.max_term_months)) 
      errs.term = `От ${product.min_term_months} до ${product.max_term_months} мес.`;

    if (!purpose.trim()) errs.purpose = 'Укажите цель';
    if (!annualRevenue.trim()) errs.annual_revenue = 'Укажите выручку';
    if (!monthlyExpenses.trim()) errs.monthly_expenses = 'Укажите расходы';

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSave = async (shouldSubmit = false) => {
    if (!validate()) return;
    if (!companies.length) {
      setErrors({ global: 'У вас нет привязанной компании' });
      return;
    }

    setSaving(true);
    setErrors({});
    try {
      const payload = { 
        amount, 
        term_months: term, 
        purpose,
        annual_revenue: annualRevenue,
        monthly_expenses: monthlyExpenses,
        existing_debt: existingDebt
      };
      
      let currentId = appId;

      if (!currentId) {
        const created = await api.createApplication({ 
          company_id: companies[0].id, 
          product_id: productId 
        });
        currentId = created.id;
        setAppId(currentId);
      }

      await api.updateApplication(currentId, payload);

      if (shouldSubmit) {
        await api.submitApplication(currentId);
        setShowSuccess(true);
      } else {
        alert('Черновик сохранен!');
        navigate(`?product=${productId}&draft=${currentId}`, { replace: true });
      }
    } catch (e: any) {
      if (e.errors) {
        const mapped: Record<string, string> = {};
        e.errors.forEach((err: any) => { mapped[err.field] = err.message; });
        setErrors(mapped);
      } else {
        setErrors({ global: e.message });
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-center">Загрузка...</div>;
  if (!product) return <div className="p-8 text-red-500">{errors.global || 'Продукт не найден'}</div>;

  return (
    <div className="max-w-2xl mx-auto p-8 relative">
      <Link to="/" className="text-sm text-gray-500 hover:text-alfa-red mb-4 inline-block">← Назад</Link>
      
      <Card>
        <h1 className="text-2xl font-bold mb-6">{product.name}</h1>
        
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-1">Сумма, ₽</label>
            <input
              type="number"
              className={`w-full p-2 border rounded-lg ${errors.amount ? 'border-red-500' : 'border-gray-300'}`}
              value={amount}
              onChange={(e) => { setAmount(e.target.value); setErrors({...errors, amount: ''}); }}
            />
            {errors.amount && <p className="text-red-500 text-xs mt-1">{errors.amount}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Срок, мес.</label>
            <input
              type="number"
              className={`w-full p-2 border rounded-lg ${errors.term ? 'border-red-500' : 'border-gray-300'}`}
              value={term}
              onChange={(e) => { setTerm(e.target.value); setErrors({...errors, term: ''}); }}
            />
            {errors.term && <p className="text-red-500 text-xs mt-1">{errors.term}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Цель</label>
            <select
              className={`w-full p-2 border rounded-lg ${errors.purpose ? 'border-red-500' : 'border-gray-300'}`}
              value={purpose}
              onChange={(e) => { setPurpose(e.target.value); setErrors({...errors, purpose: ''}); }}
            >
              <option value="">Выберите цель</option>
              {product.purposes.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            {errors.purpose && <p className="text-red-500 text-xs mt-1">{errors.purpose}</p>}
          </div>

          {/* Новые поля для скоринга */}
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Финансовые показатели</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Годовая выручка, ₽</label>
                <input
                  type="number"
                  className={`w-full p-2 border rounded-lg ${errors.annual_revenue ? 'border-red-500' : 'border-gray-300'}`}
                  value={annualRevenue}
                  onChange={(e) => { setAnnualRevenue(e.target.value); setErrors({...errors, annual_revenue: ''}); }}
                />
                {errors.annual_revenue && <p className="text-red-500 text-xs mt-1">{errors.annual_revenue}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Ежемесячные расходы, ₽</label>
                <input
                  type="number"
                  className={`w-full p-2 border rounded-lg ${errors.monthly_expenses ? 'border-red-500' : 'border-gray-300'}`}
                  value={monthlyExpenses}
                  onChange={(e) => { setMonthlyExpenses(e.target.value); setErrors({...errors, monthly_expenses: ''}); }}
                />
                {errors.monthly_expenses && <p className="text-red-500 text-xs mt-1">{errors.monthly_expenses}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Текущая задолженность, ₽</label>
                <input
                  type="number"
                  className={`w-full p-2 border rounded-lg ${errors.existing_debt ? 'border-red-500' : 'border-gray-300'}`}
                  value={existingDebt}
                  onChange={(e) => { setExistingDebt(e.target.value); setErrors({...errors, existing_debt: ''}); }}
                />
                {errors.existing_debt && <p className="text-red-500 text-xs mt-1">{errors.existing_debt}</p>}
              </div>
            </div>
          </div>

          {errors.global && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{errors.global}</div>}

          <div className="pt-4 flex gap-3 border-t">
            <Button variant="secondary" onClick={() => handleSave(false)} disabled={saving} className="flex-1">
              Сохранить черновик
            </Button>
            <Button onClick={() => handleSave(true)} disabled={saving} className="flex-1">
              Отправить заявку
            </Button>
          </div>
        </div>
      </Card>

      {/* Модальное окно успеха */}
      {showSuccess && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-sm text-center">
            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
              ✓
            </div>
            <h3 className="text-xl font-bold mb-2">Заявка отправлена!</h3>
            <p className="text-gray-500 mb-6">Ваша заявка находится на рассмотрении. Мы уведомим вас о решении.</p>
            <Button className="w-full" onClick={() => navigate('/profile')}>
              Перейти к моим заявкам
            </Button>
          </Card>
        </div>
      )}
    </div>
  );
};