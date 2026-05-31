import type {
  TicketsRecord,
  CommentsRecord,
  AttachmentsRecord,
  UsersRecord,
  NotificationsRecord
} from '$lib/types/pocketbase';
import { sseManager } from './sseManager';
import type { TypedPocketBase } from '$lib/types/pocketbase';

const getRelatedUserIds = (ticket: TicketsRecord): string[] => {
  const userIds = new Set<string>();

  if (ticket.creator) userIds.add(ticket.creator);
  if (ticket.assignee) userIds.add(ticket.assignee);
  if (ticket.watchers) {
    for (const watcher of ticket.watchers) {
      userIds.add(watcher);
    }
  }

  return Array.from(userIds);
};

const createNotification = async (
  pb: TypedPocketBase,
  data: Omit<NotificationsRecord, 'id' | 'created' | 'updated'>
): Promise<NotificationsRecord> => {
  return await pb.collection('notifications').create(data);
};

export const notifyStatusChange = async (
  pb: TypedPocketBase,
  ticket: TicketsRecord,
  actor: UsersRecord,
  oldStatus: string,
  newStatus: string
): Promise<void> => {
  const statusLabels: Record<string, string> = {
    pending: '待接单',
    processing: '处理中',
    reviewing: '审核中',
    completed: '已完成'
  };

  const message = `${actor.name} 将工单状态从「${statusLabels[oldStatus] || oldStatus}」改为「${statusLabels[newStatus] || newStatus}」`;
  const relatedUserIds = getRelatedUserIds(ticket).filter((id) => id !== actor.id);

  for (const userId of relatedUserIds) {
    const notification = await createNotification(pb, {
      user: userId,
      ticket: ticket.id,
      type: 'status_change',
      message,
      read: false
    });

    sseManager.sendToUser(userId, {
      ...notification,
      ticket_title: ticket.title
    });
  }
};

export const notifyComment = async (
  pb: TypedPocketBase,
  ticket: TicketsRecord,
  comment: CommentsRecord,
  actor: UsersRecord
): Promise<void> => {
  const message = `${actor.name} 发表了评论`;
  const relatedUserIds = getRelatedUserIds(ticket).filter((id) => id !== actor.id);

  for (const userId of relatedUserIds) {
    const notification = await createNotification(pb, {
      user: userId,
      ticket: ticket.id,
      type: 'comment',
      message,
      read: false
    });

    sseManager.sendToUser(userId, {
      ...notification,
      ticket_title: ticket.title
    });
  }

  if (comment.mentions && comment.mentions.length > 0) {
    const mentionMessage = `${actor.name} 在评论中@了你`;
    for (const mentionedUserId of comment.mentions) {
      if (mentionedUserId !== actor.id && !relatedUserIds.includes(mentionedUserId)) {
        const notification = await createNotification(pb, {
          user: mentionedUserId,
          ticket: ticket.id,
          type: 'mention',
          message: mentionMessage,
          read: false
        });

        sseManager.sendToUser(mentionedUserId, {
          ...notification,
          ticket_title: ticket.title
        });
      }
    }
  }
};

export const notifyAssignment = async (
  pb: TypedPocketBase,
  ticket: TicketsRecord,
  actor: UsersRecord,
  assignee: UsersRecord
): Promise<void> => {
  if (actor.id === assignee.id) return;

  const message = `${actor.name} 将工单分配给了你`;
  const notification = await createNotification(pb, {
    user: assignee.id,
    ticket: ticket.id,
    type: 'assignment',
    message,
    read: false
  });

  sseManager.sendToUser(assignee.id, {
    ...notification,
    ticket_title: ticket.title
  });
};

export const notifyAttachment = async (
  pb: TypedPocketBase,
  ticket: TicketsRecord,
  attachment: AttachmentsRecord,
  actor: UsersRecord
): Promise<void> => {
  const message = `${actor.name} 上传了附件：${attachment.filename}`;
  const relatedUserIds = getRelatedUserIds(ticket).filter((id) => id !== actor.id);

  for (const userId of relatedUserIds) {
    const notification = await createNotification(pb, {
      user: userId,
      ticket: ticket.id,
      type: 'attachment',
      message,
      read: false
    });

    sseManager.sendToUser(userId, {
      ...notification,
      ticket_title: ticket.title
    });
  }
};
