import { useEffect, useState } from 'react';

export interface User {
  interests: string[];
}

function apiBase() {
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000`;
}

export function useUser(uid: string | number) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    if (uid === null || uid === undefined) return;
    fetch(`${apiBase()}/user/${uid}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, [uid]);
  return user;
}
