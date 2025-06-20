import { useState, useEffect, useMemo } from 'react';
import { useFeed } from './hooks/useFeed';
import { useUser } from './hooks/useUser';
import { PostCard } from './components/PostCard';
import { UserInterests } from './components/UserInterests';
import { toggleTopic } from './utils';

export default function App({ initialUid }: { initialUid?: string }) {
  const [uid, setUid] = useState(Number(initialUid ?? 0));
  const feed = useFeed(String(uid));
  const user = useUser(String(uid));
  const [activeTopic, setActiveTopic] = useState<string | null>(null);

  const topicFilter = useMemo(() => {
    if (!activeTopic) return null;
    if (!user?.interests?.includes(activeTopic)) return null;
    if (!feed.messages.some((m) => m.topic === activeTopic)) return null;
    return activeTopic;
  }, [activeTopic, user?.interests, feed.messages]);

  useEffect(() => {
    setActiveTopic(null);
  }, [uid]);

  useEffect(() => {
    if (activeTopic && user?.interests && !user.interests.includes(activeTopic)) {
      setActiveTopic(null);
    }
  }, [user?.interests, activeTopic]);

  return (
    <div className="min-h-screen bg-[#f7f7fa]">
      <header className="sticky top-0 bg-[#f7f7fa] py-4 mb-4 shadow-sm">
        <div className="max-w-3xl mx-auto space-y-2">
          <div className="flex items-end gap-4">
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
          <UserInterests
            interests={user?.interests ?? []}
            activeTopic={topicFilter}
            onTagClick={(t) => setActiveTopic((prev) => toggleTopic(prev, t))}
          />
        </div>
      </header>
      <div className="max-w-3xl mx-auto space-y-6">
        {user?.interests?.length ? (
          <section>
            <h2 className="font-bold mb-1">Interests</h2>
            <div className="mb-2">
              <UserInterests
                interests={user.interests}
                activeTopic={topicFilter}
                onTagClick={(t) =>
                  setActiveTopic((prev) => toggleTopic(prev, t))
                }
              />
            </div>
          </section>
        ) : null}
        {feed.pending.length > 0 && !feed.loading && (
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
              .filter((m) => !topicFilter || m.topic === topicFilter)
              .map((m) => (
                <PostCard
                  key={m.id}
                  {...m}
                  activeTopic={topicFilter}
                  onTagClick={(t) =>
                    setActiveTopic((prev) => toggleTopic(prev, t))
                  }
                />
              ))}
          </div>
          {!feed.ready && <div>connecting…</div>}
          {feed.ready && feed.loading && <div className="animate-pulse">loading…</div>}
        </div>
      </div>
    </div>
  );
}
