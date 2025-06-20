import React from 'react';
import { TagChip } from './TagChip';

export interface UserInterestsProps {
  interests?: string[];
  activeTopic?: string | null;
  onTagClick?: (t: string) => void;
}

export function UserInterests({ interests = [], activeTopic, onTagClick }: UserInterestsProps) {
  if (!interests.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {interests.map((t) => (
        <TagChip
          key={t}
          label={t}
          active={activeTopic === t}
          onClick={() => onTagClick?.(t)}
        />
      ))}
    </div>
  );
}
