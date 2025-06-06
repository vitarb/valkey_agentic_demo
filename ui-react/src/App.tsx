import { useState } from 'react';
import { useFeed } from './hooks/useFeed';
import { useUser } from './hooks/useUser';
import { PostCard } from './components/PostCard';
import { TagChip } from './components/TagChip';
import { toggleTopic } from './utils';

export default function App() {
  const [uid, setUid] = useState(0);
  const feed = useFeed(String(uid));
  const user = useUser(String(uid));
  const [activeTopic, setActiveTopic] = useState<string | null>(null);

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
        </div>
      </header>
      <div className="max-w-3xl mx-auto space-y-6">
        {user?.interests && (
          <div className="mb-2">
            {user.interests.map((t) => (
              <TagChip
                key={t}
                label={t}
                active={activeTopic === t}
                onClick={() => setActiveTopic((prev) => toggleTopic(prev, t))}
              />
            ))}
          </div>
        )}
        {feed.pending.length > 0 && (
          <button
            className="fixed top-16 right-4 bg-blue-600 text-white px-3 py-1 rounded"
            onClick={feed.refresh}
          >
            🔄 Refresh ({feed.pending.length})
          </button>
        )}
        <div>
          <h2 className="font-bold mb-2">Feed</h2>
          <div className="space-y-3">
            {feed.messages
              .filter((m) => !activeTopic || m.topic === activeTopic)
              .map((m) => (
                <PostCard
                  key={m.id}
                  {...m}
                  activeTopic={activeTopic}
                  onTagClick={(t) =>
                    setActiveTopic((prev) => toggleTopic(prev, t))
                  }
                />
              ))}
          </div>
          {!feed.ready && <div>connecting…</div>}
        </div>
      </div>
    </div>
  );
}
