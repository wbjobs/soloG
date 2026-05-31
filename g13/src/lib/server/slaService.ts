import type {
  TicketsRecord,
  UsersRecord,
  SlaConfigsRecord,
  EscalationHistoryRecord,
  NotificationsRecord
} from '$lib/types/pocketbase';
import type { TypedPocketBase } from '$lib/types/pocketbase';
import { sseManager } from './sseManager';

const SLA_CONFIGS: Record<string, SlaConfigsRecord> = {
  low: {
    id: 'sla_low',
    priority: 'low',
    response_hours: 24,
    resolution_hours: 72,
    escalation_hours: 48,
    created: '',
    updated: ''
  },
  medium: {
    id: 'sla_medium',
    priority: 'medium',
    response_hours: 8,
    resolution_hours: 24,
    escalation_hours: 12,
    created: '',
    updated: ''
  },
  high: {
    id: 'sla_high',
    priority: 'high',
    response_hours: 2,
    resolution_hours: 8,
    escalation_hours: 4,
    created: '',
    updated: ''
  }
};

export const calculateSlaDeadline = (
  createdAt: string,
  priority: 'low' | 'medium' | 'high'
): string => {
  const config = SLA_CONFIGS[priority];
  const created = new Date(createdAt);
  const deadline = new Date(created.getTime() + config.escalation_hours * 60 * 60 * 1000);
  return deadline.toISOString();
};

export const isTicketOverdue = (ticket: TicketsRecord): boolean => {
  if (!ticket.sla_deadline || ticket.status === 'completed') {
    return false;
  }
  return new Date() > new Date(ticket.sla_deadline);
};

export const getSlaStatus = (
  ticket: TicketsRecord
): { status: 'normal' | 'warning' | 'overdue'; remainingMinutes: number } => {
  if (!ticket.sla_deadline || ticket.status === 'completed') {
    return { status: 'normal', remainingMinutes: Infinity };
  }

  const now = new Date();
  const deadline = new Date(ticket.sla_deadline);
  const remainingMs = deadline.getTime() - now.getTime();
  const remainingMinutes = Math.floor(remainingMs / (1000 * 60));

  if (remainingMinutes <= 0) {
    return { status: 'overdue', remainingMinutes };
  }

  const config = SLA_CONFIGS[ticket.priority];
  const warningThreshold = config.escalation_hours * 0.25 * 60;

  if (remainingMinutes <= warningThreshold) {
    return { status: 'warning', remainingMinutes };
  }

  return { status: 'normal', remainingMinutes };
};

export const checkAndEscalateTicket = async (
  pb: TypedPocketBase,
  ticket: TicketsRecord
): Promise<boolean> => {
  if (ticket.status === 'completed') {
    return false;
  }

  const slaStatus = getSlaStatus(ticket);
  if (slaStatus.status !== 'overdue') {
    return false;
  }

  const currentLevel = ticket.escalation_level || 0;
  if (currentLevel >= 3) {
    return false;
  }

  try {
    if (!ticket.assignee) {
      return false;
    }

    const assignee = await pb.collection('users').getOne(ticket.assignee);
    let nextAssignee: UsersRecord | null = null;

    if (assignee.manager) {
      nextAssignee = await pb.collection('users').getOne(assignee.manager);
    } else {
      const admins = await pb.collection('users').getList(1, 1, {
        filter: 'role = "admin"'
      });
      if (admins.items.length > 0) {
        nextAssignee = admins.items[0] as UsersRecord;
      }
    }

    if (!nextAssignee || nextAssignee.id === assignee.id) {
      return false;
    }

    const newLevel = currentLevel + 1;

    await pb.collection('tickets').update(ticket.id, {
      assignee: nextAssignee.id,
      escalation_level: newLevel,
      watchers: [...(ticket.watchers || []), assignee.id]
    });

    await pb.collection('escalation_history').create({
      ticket: ticket.id,
      from_user: assignee.id,
      to_user: nextAssignee.id,
      reason: `SLA 超时自动升级（优先级：${ticket.priority}，已超时 ${Math.abs(slaStatus.remainingMinutes)} 分钟）`,
      level: newLevel
    });

    const notification = await pb.collection('notifications').create({
      user: nextAssignee.id,
      ticket: ticket.id,
      type: 'sla_escalation',
      message: `工单「${ticket.title}」因 SLA 超时已自动升级到您处理`,
      read: false
    });

    sseManager.sendToUser(nextAssignee.id, {
      ...notification,
      ticket_title: ticket.title
    });

    await pb.collection('notifications').create({
      user: assignee.id,
      ticket: ticket.id,
      type: 'sla_escalation',
      message: `您负责的工单「${ticket.title}」因 SLA 超时已自动升级`,
      read: false
    });

    console.log(`[SLA] Ticket ${ticket.id} escalated from ${assignee.name} to ${nextAssignee.name} (level ${newLevel})`);
    return true;
  } catch (e) {
    console.error('[SLA] Failed to escalate ticket:', ticket.id, e);
    return false;
  }
};

export const checkAllOverdueTickets = async (pb: TypedPocketBase): Promise<number> => {
  try {
    const tickets = await pb.collection('tickets').getFullList({
      filter: 'status != "completed" && sla_deadline != null'
    });

    let escalatedCount = 0;

    for (const ticket of tickets) {
      const escalated = await checkAndEscalateTicket(pb, ticket);
      if (escalated) {
        escalatedCount++;
      }
    }

    console.log(`[SLA] Checked ${tickets.length} tickets, escalated ${escalatedCount}`);
    return escalatedCount;
  } catch (e) {
    console.error('[SLA] Failed to check overdue tickets:', e);
    return 0;
  }
};

let slaCheckInterval: NodeJS.Timeout | null = null;

export const startSlaMonitoring = (pb: TypedPocketBase) => {
  if (slaCheckInterval) {
    return;
  }

  console.log('[SLA] Starting SLA monitoring');

  checkAllOverdueTickets(pb);

  slaCheckInterval = setInterval(() => {
    checkAllOverdueTickets(pb);
  }, 5 * 60 * 1000);
};

export const stopSlaMonitoring = () => {
  if (slaCheckInterval) {
    clearInterval(slaCheckInterval);
    slaCheckInterval = null;
    console.log('[SLA] SLA monitoring stopped');
  }
};

export const formatRemainingTime = (minutes: number): string => {
  if (minutes <= 0) {
    return '已超时';
  }

  const days = Math.floor(minutes / (24 * 60));
  const hours = Math.floor((minutes % (24 * 60)) / 60);
  const mins = minutes % 60;

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}天`);
  if (hours > 0) parts.push(`${hours}小时`);
  if (mins > 0) parts.push(`${mins}分钟`);

  return parts.join(' ') || '即将超时';
};
