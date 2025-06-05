import { useState } from 'react';
import { useFeed } from './hooks/useFeed';
import { useTopic } from './hooks/useTopic';

const TOPICS = [
  'politics',
  'business',
  'technology',
  'sports',
  'health',
  'climate',
  'science',
  'education',
  'entertainment',
  'finance',
];

export default function App() {
  const feed = useFeed('0');
  const [slug, setSlug] = useState('technology');
  const topic = useTopic(slug);
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-bold">Feed</h2>
        <ul>
          {feed.messages.map((m) => (
            <li key={m.id}>{m.text}</li>
          ))}
        </ul>
        {!feed.ready && <div>connecting…</div>}
      </div>
      <div>
        <h2 className="font-bold">Topic</h2>
        <select
          className="border ml-2"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
        >
          {TOPICS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <ul>
          {topic.messages.map((m) => (
            <li key={m.id}>{m.text}</li>
          ))}
        </ul>
        {!topic.ready && <div>connecting…</div>}
      </div>
    </div>
  );
}
