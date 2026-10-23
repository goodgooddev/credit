// import React, { useState } from 'react';
// import { Link, useNavigate } from 'react-router-dom';
// import { api } from '../api/client';
// import { Card, Button } from '../components/UI';

// export const Register = () => {
//   const [formData, setFormData] = useState({
//     name: '',
//     email: '',
//     password: '',
//     confirmPassword: '',
//   });
//   const [error, setError] = useState('');
//   const [loading, setLoading] = useState(false);
//   const navigate = useNavigate();

//   const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
//     setFormData({ ...formData, [e.target.name]: e.target.value });
//   };

//   const handleSubmit = async (e: React.FormEvent) => {
//     e.preventDefault();
//     setError('');

//     if (formData.password !== formData.confirmPassword) {
//       setError('Пароли не совпадают');
//       return;
//     }

//     setLoading(true);
//     try {
//       await api.register({
//         name: formData.name,
//         email: formData.email,
//         password: formData.password,
//       });
//       navigate('/profile');
//     } catch (err: any) {
//       setError(err.message || 'Ошибка регистрации');
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-[80vh] flex items-center justify-center p-4">
//       <Card className="w-full max-w-md">
//         <div className="text-center mb-6">
//           <h1 className="text-2xl font-bold text-alfa-text">Создать аккаунт</h1>
//           <p className="text-gray-500 text-sm mt-1">Подключите свой бизнес к Альфа-Кабинету</p>
//         </div>

//         <form onSubmit={handleSubmit} className="space-y-4">
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Ваше имя</label>
//             <input
//               type="text"
//               name="name"
//               required
//               className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
//               placeholder="Иван Иванов"
//               value={formData.name}
//               onChange={handleChange}
//             />
//           </div>
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
//             <input
//               type="email"
//               name="email"
//               required
//               className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
//               placeholder="ivan@romashka.ru"
//               value={formData.email}
//               onChange={handleChange}
//             />
//           </div>
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
//             <input
//               type="password"
//               name="password"
//               required
//               className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
//               placeholder="••••••"
//               value={formData.password}
//               onChange={handleChange}
//             />
//           </div>
//           <div>
//             <label className="block text-sm font-medium text-gray-700 mb-1">Повторите пароль</label>
//             <input
//               type="password"
//               name="confirmPassword"
//               required
//               className="w-full p-3 border border-gray-300 rounded-lg outline-none focus:border-alfa-red focus:ring-1 focus:ring-alfa-red transition-all"
//               placeholder="••••••"
//               value={formData.confirmPassword}
//               onChange={handleChange}
//             />
//           </div>

//           {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>}

//           <Button type="submit" className="w-full" disabled={loading}>
//             {loading ? 'Регистрация...' : 'Зарегистрироваться'}
//           </Button>
//         </form>

//         <div className="mt-6 text-center text-sm text-gray-500">
//           Уже есть аккаунт? <Link to="/login" className="text-alfa-red font-medium hover:underline">Войти</Link>
//         </div>
//       </Card>
//     </div>
//   );
// };