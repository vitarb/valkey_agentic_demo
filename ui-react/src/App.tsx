import { useState } from 'react';
import { useFeed } from './hooks/useFeed';
import { useTopic } from './hooks/useTopic';
import { PostCard } from './components/PostCard';

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
  const [uid, setUid] = useState(0);
  const feed = useFeed(String(uid));
  const [slug, setSlug] = useState('technology');
  const topic = useTopic(slug);

  return (
    <div className="min-h-screen bg-[#f7f7fa]">
      <header className="sticky top-0 bg-[#f7f7fa] py-4 mb-4 shadow-sm">
        <div className="max-w-3xl mx-auto flex items-end gap-4">
          <h1 className="text-xl font-bold flex-1">Valkey Agentic Demo</h1>
          <label className="text-sm">User ID</label>
          <input
            type="number"
            className="border rounded px-2 py-1 w-20"
            value={uid}
            min={0}
            onChange={(e) => setUid(Number(e.target.value))}
          />
          <select
            className="border rounded px-2 py-1"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
          >
            {TOPICS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </header>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="font-bold mb-2">Feed</h2>
          <div className="space-y-3">
            {feed.messages.map((m) => (
              <PostCard key={m.id} {...m} />
            ))}
          </div>
          {!feed.ready && <div>connecting…</div>}
        </div>
        <div>
          <h2 className="font-bold mb-2">Topic</h2>
          <div className="space-y-3">
            {topic.messages.map((m) => (
              <PostCard key={m.id} {...m} />
            ))}
          </div>
          {!topic.ready && <div>connecting…</div>}
        </div>
      </div>
    </div>
  );
}
