import React from 'react';
import { TagChip } from './TagChip';

export interface PostCardProps {
  title: string;
  summary?: string;
  body?: string;
  tags?: string[];
  topic?: string;
  activeTopic?: string | null;
  onTagClick?: (t: string) => void;
}

export function PostCard({
  title,
  summary,
  body,
  tags = [],
  topic,
  activeTopic,
  onTagClick,
}: PostCardProps) {
  const chips = Array.from(new Set([...(tags ?? []), topic].filter(Boolean)));
  return (
    <details className="rounded-2xl shadow-sm p-4 bg-white">
      <summary className="list-none">
        <h3 className="font-bold truncate" title={title}>
          {title}
        </h3>
        {summary || body ? (
          <p className="text-sm text-slate-700 line-clamp-2 mt-1">
            {summary ?? body}
          </p>
        ) : null}
        <div className="mt-2">
          {chips.map((t) => (
            <TagChip
              key={t}
              label={t}
              active={activeTopic === t}
              onClick={() => onTagClick?.(t)}
            />
          ))}
        </div>
      </summary>
      {body && <p className="mt-2 whitespace-pre-wrap text-sm">{body}</p>}
    </details>
  );
}
