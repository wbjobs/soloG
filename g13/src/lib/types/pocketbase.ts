export type TicketStatus = 'pending' | 'processing' | 'reviewing' | 'completed';

export interface UsersRecord {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  manager?: string;
  role?: 'user' | 'manager' | 'admin';
  created: string;
  updated: string;
}

export interface TicketsRecord {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: 'low' | 'medium' | 'high';
  creator: string;
  assignee?: string;
  watchers?: string[];
  sla_deadline?: string;
  escalation_level?: number;
  total_hours?: number;
  created: string;
  updated: string;
}

export interface TicketsResponse extends TicketsRecord {
  expand?: {
    creator?: UsersRecord;
    assignee?: UsersRecord;
    watchers?: UsersRecord[];
  };
}

export interface CommentsRecord {
  id: string;
  ticket: string;
  author: string;
  content: string;
  mentions?: string[];
  created: string;
  updated: string;
}

export interface CommentsResponse extends CommentsRecord {
  expand?: {
    author?: UsersRecord;
    mentions?: UsersRecord[];
  };
}

export interface AttachmentsRecord {
  id: string;
  ticket: string;
  uploader: string;
  file: string;
  filename: string;
  size: number;
  created: string;
  updated: string;
}

export interface AttachmentsResponse extends AttachmentsRecord {
  expand?: {
    uploader?: UsersRecord;
  };
}

export interface ActivityLogsRecord {
  id: string;
  ticket: string;
  actor: string;
  action: string;
  old_value?: string;
  new_value?: string;
  metadata?: string;
  created: string;
}

export interface ActivityLogsResponse extends ActivityLogsRecord {
  expand?: {
    actor?: UsersRecord;
  };
}

export interface NotificationsRecord {
  id: string;
  user: string;
  ticket: string;
  type: 'status_change' | 'comment' | 'mention' | 'assignment' | 'attachment' | 'sla_escalation';
  message: string;
  read: boolean;
  created: string;
}

export interface TimeLogsRecord {
  id: string;
  ticket: string;
  user: string;
  hours: number;
  description: string;
  log_date: string;
  created: string;
  updated: string;
}

export interface TimeLogsResponse extends TimeLogsRecord {
  expand?: {
    user?: UsersRecord;
    ticket?: TicketsRecord;
  };
}

export interface SlaConfigsRecord {
  id: string;
  priority: 'low' | 'medium' | 'high';
  response_hours: number;
  resolution_hours: number;
  escalation_hours: number;
  created: string;
  updated: string;
}

export interface EscalationHistoryRecord {
  id: string;
  ticket: string;
  from_user: string;
  to_user: string;
  reason: string;
  level: number;
  created: string;
}

export interface TypedPocketBase {
  collection(idOrName: 'users'): import('pocketbase').RecordService<UsersRecord>;
  collection(idOrName: 'tickets'): import('pocketbase').RecordService<TicketsRecord>;
  collection(idOrName: 'comments'): import('pocketbase').RecordService<CommentsRecord>;
  collection(idOrName: 'attachments'): import('pocketbase').RecordService<AttachmentsRecord>;
  collection(idOrName: 'activity_logs'): import('pocketbase').RecordService<ActivityLogsRecord>;
  collection(idOrName: 'notifications'): import('pocketbase').RecordService<NotificationsRecord>;
  collection(idOrName: 'time_logs'): import('pocketbase').RecordService<TimeLogsRecord>;
  collection(idOrName: 'sla_configs'): import('pocketbase').RecordService<SlaConfigsRecord>;
  collection(idOrName: 'escalation_history'): import('pocketbase').RecordService<EscalationHistoryRecord>;
}
