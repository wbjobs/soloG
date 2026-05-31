import type {
  TicketsRecord,
  UsersRecord,
  CommentsRecord,
  AttachmentsRecord,
  ActivityLogsRecord,
  TimeLogsRecord
} from '$lib/types/pocketbase';
import type { TypedPocketBase } from '$lib/types/pocketbase';
import {
  notifyStatusChange,
  notifyComment,
  notifyAssignment,
  notifyAttachment
} from './notificationService';
import { calculateSlaDeadline } from './slaService';

export const logActivity = async (
  pb: TypedPocketBase,
  ticketId: string,
  actorId: string,
  action: string,
  oldValue?: string,
  newValue?: string,
  metadata?: Record<string, unknown>
): Promise<ActivityLogsRecord> => {
  return await pb.collection('activity_logs').create({
    ticket: ticketId,
    actor: actorId,
    action,
    old_value: oldValue,
    new_value: newValue,
    metadata: metadata ? JSON.stringify(metadata) : undefined
  });
};

export const createTicket = async (
  pb: TypedPocketBase,
  data: {
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
    assignee?: string;
  },
  creator: UsersRecord
): Promise<TicketsRecord> => {
  const now = new Date().toISOString();
  const slaDeadline = calculateSlaDeadline(now, data.priority);

  const ticket = await pb.collection('tickets').create({
    ...data,
    status: 'pending',
    creator: creator.id,
    watchers: [creator.id],
    sla_deadline: slaDeadline,
    escalation_level: 0,
    total_hours: 0
  });

  await logActivity(pb, ticket.id, creator.id, 'create_ticket', undefined, undefined, {
    title: data.title
  });

  if (data.assignee && data.assignee !== creator.id) {
    const assignee = await pb.collection('users').getOne(data.assignee);
    await notifyAssignment(pb, ticket, creator, assignee);
  }

  return ticket;
};

export const updateTicketStatus = async (
  pb: TypedPocketBase,
  ticketId: string,
  newStatus: 'pending' | 'processing' | 'reviewing' | 'completed',
  actor: UsersRecord
): Promise<TicketsRecord> => {
  const ticket = await pb.collection('tickets').getOne(ticketId);
  const oldStatus = ticket.status;

  if (oldStatus === newStatus) {
    return ticket;
  }

  const updatedTicket = await pb.collection('tickets').update(ticketId, {
    status: newStatus
  });

  await logActivity(pb, ticketId, actor.id, 'change_status', oldStatus, newStatus);

  await notifyStatusChange(pb, updatedTicket, actor, oldStatus, newStatus);

  return updatedTicket;
};

export const updateTicketAssignee = async (
  pb: TypedPocketBase,
  ticketId: string,
  assigneeId: string,
  actor: UsersRecord
): Promise<TicketsRecord> => {
  const ticket = await pb.collection('tickets').getOne(ticketId);
  const oldAssignee = ticket.assignee;

  const updatedTicket = await pb.collection('tickets').update(ticketId, {
    assignee: assigneeId
  });

  if (assigneeId && oldAssignee !== assigneeId) {
    const watchers = updatedTicket.watchers || [];
    if (!watchers.includes(assigneeId)) {
      watchers.push(assigneeId);
      await pb.collection('tickets').update(ticketId, { watchers });
    }

    const assignee = await pb.collection('users').getOne(assigneeId);
    await notifyAssignment(pb, updatedTicket, actor, assignee);
  }

  await logActivity(pb, ticketId, actor.id, 'assign_ticket', oldAssignee, assigneeId);

  return updatedTicket;
};

export const addComment = async (
  pb: TypedPocketBase,
  ticketId: string,
  content: string,
  mentions: string[],
  actor: UsersRecord
): Promise<CommentsRecord> => {
  const ticket = await pb.collection('tickets').getOne(ticketId);

  const comment = await pb.collection('comments').create({
    ticket: ticketId,
    author: actor.id,
    content,
    mentions
  });

  const watchers = ticket.watchers || [];
  let updated = false;
  for (const mentioned of mentions) {
    if (!watchers.includes(mentioned)) {
      watchers.push(mentioned);
      updated = true;
    }
  }
  if (updated) {
    await pb.collection('tickets').update(ticketId, { watchers });
  }

  await logActivity(pb, ticketId, actor.id, 'add_comment', undefined, undefined, {
    comment_id: comment.id,
    content_length: content.length
  });

  await notifyComment(pb, ticket, comment, actor);

  return comment;
};

export const addAttachment = async (
  pb: TypedPocketBase,
  ticketId: string,
  file: File,
  actor: UsersRecord
): Promise<AttachmentsRecord> => {
  const ticket = await pb.collection('tickets').getOne(ticketId);

  const formData = new FormData();
  formData.append('ticket', ticketId);
  formData.append('uploader', actor.id);
  formData.append('filename', file.name);
  formData.append('size', String(file.size));
  formData.append('file', file);

  const attachment = await pb.collection('attachments').create(formData);

  await logActivity(pb, ticketId, actor.id, 'upload_attachment', undefined, undefined, {
    attachment_id: attachment.id,
    filename: file.name,
    size: file.size
  });

  await notifyAttachment(pb, ticket, attachment, actor);

  return attachment;
};

export const addWatcher = async (
  pb: TypedPocketBase,
  ticketId: string,
  userId: string,
  actor: UsersRecord
): Promise<TicketsRecord> => {
  const ticket = await pb.collection('tickets').getOne(ticketId);
  const watchers = ticket.watchers || [];

  if (!watchers.includes(userId)) {
    watchers.push(userId);
    const updatedTicket = await pb.collection('tickets').update(ticketId, { watchers });

    await logActivity(pb, ticketId, actor.id, 'add_watcher', undefined, userId);

    return updatedTicket;
  }

  return ticket;
};

export const addTimeLog = async (
  pb: TypedPocketBase,
  ticketId: string,
  hours: number,
  description: string,
  logDate: string,
  actor: UsersRecord
): Promise<TimeLogsRecord> => {
  const timeLog = await pb.collection('time_logs').create({
    ticket: ticketId,
    user: actor.id,
    hours,
    description,
    log_date: logDate
  });

  const ticket = await pb.collection('tickets').getOne(ticketId);
  const currentTotal = ticket.total_hours || 0;
  await pb.collection('tickets').update(ticketId, {
    total_hours: currentTotal + hours
  });

  await logActivity(pb, ticketId, actor.id, 'add_time_log', undefined, undefined, {
    hours,
    description
  });

  return timeLog;
};

export const getTicketTimeLogs = async (
  pb: TypedPocketBase,
  ticketId: string
): Promise<TimeLogsRecord[]> => {
  return await pb.collection('time_logs').getFullList({
    filter: `ticket = "${ticketId}"`,
    sort: '-log_date',
    expand: 'user'
  });
};

export const getTimeReport = async (
  pb: TypedPocketBase,
  startDate: string,
  endDate: string,
  userId?: string
): Promise<{
  totalHours: number;
  ticketCount: number;
  byUser: Array<{ userId: string; userName: string; hours: number; ticketCount: number }>;
  byTicket: Array<{ ticketId: string; ticketTitle: string; hours: number; userCount: number }>;
  logs: TimeLogsRecord[];
}> => {
  const filter = [`log_date >= "${startDate}"`, `log_date <= "${endDate}"`];
  if (userId) {
    filter.push(`user = "${userId}"`);
  }

  const logs = await pb.collection('time_logs').getFullList({
    filter: filter.join(' && '),
    sort: '-log_date',
    expand: 'user,ticket'
  });

  const totalHours = logs.reduce((sum, log) => sum + log.hours, 0);
  const uniqueTickets = new Set(logs.map((log) => log.ticket));

  const byUserMap = new Map<string, { userName: string; hours: number; ticketCount: Set<string> }>();
  const byTicketMap = new Map<string, { ticketTitle: string; hours: number; userCount: Set<string> }>();

  for (const log of logs) {
    const user = (log as unknown as { expand?: { user?: UsersRecord } }).expand?.user;
    const ticket = (log as unknown as { expand?: { ticket?: TicketsRecord } }).expand?.ticket;

    if (!byUserMap.has(log.user)) {
      byUserMap.set(log.user, {
        userName: user?.name || '未知用户',
        hours: 0,
        ticketCount: new Set()
      });
    }
    const userData = byUserMap.get(log.user)!;
    userData.hours += log.hours;
    userData.ticketCount.add(log.ticket);

    if (!byTicketMap.has(log.ticket)) {
      byTicketMap.set(log.ticket, {
        ticketTitle: ticket?.title || '未知工单',
        hours: 0,
        userCount: new Set()
      });
    }
    const ticketData = byTicketMap.get(log.ticket)!;
    ticketData.hours += log.hours;
    ticketData.userCount.add(log.user);
  }

  const byUser = Array.from(byUserMap.entries()).map(([userId, data]) => ({
    userId,
    userName: data.userName,
    hours: data.hours,
    ticketCount: data.ticketCount.size
  }));

  const byTicket = Array.from(byTicketMap.entries()).map(([ticketId, data]) => ({
    ticketId,
    ticketTitle: data.ticketTitle,
    hours: data.hours,
    userCount: data.userCount.size
  }));

  return {
    totalHours,
    ticketCount: uniqueTickets.size,
    byUser,
    byTicket,
    logs
  };
};
