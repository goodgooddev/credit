import React from 'react';
import clsx from 'clsx';

export const Button = ({
  children,
  className,
  variant = 'primary',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger';
}) => (
  <button
    className={clsx(
      'px-5 py-2.5 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-sm',
      variant === 'primary' && 'bg-alfa-red text-white hover:bg-alfa-red-hover shadow-sm',
      variant === 'secondary' && 'bg-white text-alfa-text border border-gray-300 hover:bg-gray-50 shadow-sm',
      variant === 'danger' && 'bg-white text-red-600 border border-red-200 hover:bg-red-50 shadow-sm',
      className,
    )}
    {...props}
  >
    {children}
  </button>
);

export const Card = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <div className={clsx('bg-white p-6 rounded-2xl shadow-sm border border-gray-100', className)}>
    {children}
  </div>
);