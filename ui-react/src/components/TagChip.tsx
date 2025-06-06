import React from 'react';

export interface TagChipProps {
  label: string;
}

export function TagChip({ label }: TagChipProps) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 bg-slate-100 text-xs rounded-full mr-1">
      {label}
    </span>
  );
}
