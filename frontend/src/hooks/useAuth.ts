import { useState, useCallback } from 'react';
import { UserRole } from '../types/chat';
import { useSessionStore } from '../store';

export function useAuth() {
  const [userId] = useState<string>(() => {
    const stored = localStorage.getItem('user_id');
    if (stored) return stored;
    const generated = `user-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('user_id', generated);
    return generated;
  });

  const { userRole, setUserRole } = useSessionStore();

  const changeRole = useCallback(
    (role: UserRole) => {
      setUserRole(role);
      localStorage.setItem('user_role', role);
    },
    [setUserRole]
  );

  return { userId, userRole, changeRole };
}
