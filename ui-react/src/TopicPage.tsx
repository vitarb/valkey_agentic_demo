import { PostCard } from './components/PostCard';
import { useTopic } from './hooks/useTopic';

export default function TopicPage({ slug }: { slug: string }) {
  const state = useTopic(slug);
  return (
    <div className="max-w-3xl mx-auto space-y-3 mt-4">
      {state.loading && <div className="animate-pulse">loading…</div>}
      {state.messages.map((m) => (
        <PostCard key={m.id} {...m} />
      ))}
      {state.pending.length > 0 && (
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded"
          onClick={state.refresh}
        >
          🔄 Refresh ({state.pending.length})
        </button>
      )}
    </div>
  );
}
