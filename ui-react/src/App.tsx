import { useFeed } from './hooks/useFeed';
import { useTopic } from './hooks/useTopic';

export default function App() {
  const feed = useFeed('0');
  const topic = useTopic('news');
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-bold">Feed</h2>
        <ul>
          {feed.map((m, i) => (
            <li key={i}>{m.text}</li>
          ))}
        </ul>
      </div>
      <div>
        <h2 className="font-bold">Topic</h2>
        <ul>
          {topic.map((m, i) => (
            <li key={i}>{m.text}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
