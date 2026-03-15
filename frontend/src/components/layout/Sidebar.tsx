import { Session, UserRole } from '../../types/chat';
import { MemoryPanel } from '../memory/MemoryPanel';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  userRole: UserRole;
  onSessionSelect: (id: string) => void;
  onRoleChange: (role: UserRole) => void;
  onNewSession: () => void;
  messageCount: number;
}

export function Sidebar(props: SidebarProps) {
  return (
    <div style={{
      width: '100%', height: '100%',
      overflow: 'hidden', display: 'flex', flexDirection: 'column',
      background: '#FFFFFF',
    }}>
      <MemoryPanel {...props} />
    </div>
  );
}
