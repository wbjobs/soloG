import { writable, derived } from 'svelte/store';
import type { NotificationsRecord } from '$lib/types/pocketbase';

export const notifications = writable<(NotificationsRecord & { ticket_title: string })[]>([]);
export const unreadCount = derived(notifications, ($notifications) =>
  $notifications.filter((n) => !n.read).length
);

let eventSource: EventSource | null = null;

export const connectSSE = () => {
  if (typeof window === 'undefined') return;

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource('/api/sse', { withCredentials: true });

  eventSource.addEventListener('connected', (event) => {
    console.log('SSE connected:', event.data);
  });

  eventSource.onmessage = (event) => {
    try {
      const notification = JSON.parse(event.data) as NotificationsRecord & { ticket_title: string };
      notifications.update(($notifications) => [notification, ...$notifications]);
    } catch (e) {
      console.error('Failed to parse SSE message:', e);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
  };
};

export const disconnectSSE = () => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
};

export const addNotification = (notification: NotificationsRecord & { ticket_title: string }) => {
  notifications.update(($notifications) => [notification, ...$notifications]);
};

export const markAllRead = async () => {
  await fetch('/api/notifications', {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ read: true })
  });
  notifications.update(($notifications) => $notifications.map((n) => ({ ...n, read: true })));
};

export const loadNotifications = async () => {
  const res = await fetch('/api/notifications?unread=true', { credentials: 'include' });
  if (res.ok) {
    const data = await res.json();
    notifications.set(data.items || []);
  }
};
