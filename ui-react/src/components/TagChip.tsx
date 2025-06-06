import React from 'react';

export interface TagChipProps {
  label: string;
  active?: boolean;
  onClick?: () => void;
}

export function TagChip({ label, active, onClick }: TagChipProps) {
  const base =
    'inline-flex items-center px-2 py-0.5 text-xs rounded-full mr-1 cursor-pointer';
  const cls = active
    ? `${base} bg-blue-600 text-white`
    : `${base} bg-slate-100 text-slate-700`;
  const handle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onClick?.();
  };
  return (
    <button type="button" className={cls} onClick={handle}>
      {label}
    </button>
  );
}
