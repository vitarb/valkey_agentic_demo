import { useEffect, useState } from 'react';

export interface User {
  interests: string[];
}

export function useUser(uid: string | number) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    if (uid === null || uid === undefined) return;
    fetch(`http://localhost:8000/user/${uid}`)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, [uid]);
  return user;
}
