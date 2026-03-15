import { create } from 'zustand';
import { Session, UserRole } from '../types/chat';

interface SessionState {
  sessions: Session[];
  activeSessionId: string | null;
  userRole: UserRole;
  setActiveSession: (id: string) => void;
  setUserRole: (role: UserRole) => void;
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSessionId: null,
  userRole: 'basic',

  setActiveSession: (id) => set({ activeSessionId: id }),
  setUserRole: (role) => set({ userRole: role }),
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),
}));
