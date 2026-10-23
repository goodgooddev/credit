const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export type UserRole = 'client' | 'staff';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface Product {
  id: number;
  code: string;
  name: string;
  description: string;
  purposes: string[];
  min_amount: string;  
  max_amount: string;
  min_term_months: number;
  max_term_months: number;
  annual_rate: string;
}

export interface Company {
  id: number;
  name: string;
  inn: string;
  industry: string;
  region: string;
  registration_date: string;
  employees_count: number;
}

export type AppStatus = 'draft' | 'submitted' | 'needs_info' | 'approved' | 'rejected' | 'counter_offer' | 'accepted';

export interface Application {
  id: number;
  company_id: number;
  product_id: number | null;
  amount: string | null;
  term_months: number | null;
  purpose: string | null;
  annual_revenue: string | null;
  monthly_expenses: string | null;
  existing_debt: string | null;
  status: AppStatus;
  risk_level: string | null;
  decision: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationDetail extends Application {
  company: Company;
  product: Product | null;
  latest_assessment: any | null;
}

export interface StaffApplication extends Application {
  company_name: string;
  owner_email: string;
}

export interface Event {
  id: number;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  actor_id: number | null;
  payload: any;
  created_at: string;
}

// --- ХЕЛПЕРЫ ---
function getHeaders() {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    if (error.errors && Array.isArray(error.errors)) {
      throw { detail: error.detail, errors: error.errors };
    }
    throw new Error(error.detail || 'Ошибка запроса');
  }

  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

// --- API ---
export const api = {
  async login(data: { email: string; password: string }) {
    const res = await request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    localStorage.setItem('access_token', res.access_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    return res.user;
  },

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  getCurrentUser(): User | null {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  },

  getProducts: () => request<Product[]>('/products'),
  
  getCompanies: () => request<Company[]>('/companies'),

  createApplication: (data: { company_id: number; product_id: number }) => 
    request<Application>('/applications', { method: 'POST', body: JSON.stringify(data) }),

  // Обновляем поля заявки (включая новые annual_revenue и т.д.)
  updateApplication: (id: number, data: any) =>
    request<Application>(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  getApplications: () => request<Application[]>('/applications'),
  
  getApplication: (id: number) => request<ApplicationDetail>(`/applications/${id}`),

  getApplicationEvents: (id: number) => request<Event[]>(`/applications/${id}/events`),

  getStaffApplications: () => request<StaffApplication[]>('/staff/applications'),
  
    // ВРЕМЕННАЯ ЗАГЛУШКА (пока нет эндпоинта в бэке)
  updateStatus: async (id: number, status: string, reason?: string) => {
    // Имитируем задержку сети
    await new Promise(r => setTimeout(r, 500));
    
    // В реальности здесь будет fetch, но для демо мы просто возвращаем успешный ответ
    console.log(`[MOCK] Заявка ${id} -> статус ${status}. Причина: ${reason || 'нет'}`);
    
    return { 
      id, 
      status, 
      decision: reason || null 
    } as Application;
  },

  submitApplication: (id: number) => 
    request<Application>(`/applications/${id}/submit`, { method: 'POST' }),
};