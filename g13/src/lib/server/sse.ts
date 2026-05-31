import type { NotificationsRecord } from '$lib/types/pocketbase';

interface Client {
  id: string;
  userId: string;
  controller: AbortController;
}

const clients = new Map<string, Client[]>();

export const addClient = (userId: string, controller: AbortController): string => {
  const clientId = crypto.randomUUID();
  const client: Client = { id: clientId, userId, controller };

  if (!clients.has(userId)) {
    clients.set(userId, []);
  }
  clients.get(userId)!.push(client);

  return clientId;
};

export const removeClient = (userId: string, clientId: string): void => {
  const userClients = clients.get(userId);
  if (userClients) {
    const index = userClients.findIndex((c) => c.id === clientId);
    if (index !== -1) {
      userClients.splice(index, 1);
    }
    if (userClients.length === 0) {
      clients.delete(userId);
    }
  }
};

export const sendNotification = (
  userId: string,
  notification: NotificationsRecord & { ticket_title: string }
): void => {
  const userClients = clients.get(userId);
  if (userClients) {
    const message = `data: ${JSON.stringify(notification)}\n\n`;
    for (const client of userClients) {
      const encoder = new TextEncoder();
      const stream = (controller: AbortController) => {
        try {
          const writer = controller.signal as unknown as WritableStreamDefaultWriter;
          writer.write(encoder.encode(message));
        } catch (e) {
          console.error('Failed to send SSE message:', e);
        }
      };
      stream(client.controller);
    }
  }
};

export const broadcastToRelatedUsers = (
  userIds: string[],
  notification: NotificationsRecord & { ticket_title: string }
): void => {
  for (const userId of userIds) {
    sendNotification(userId, notification);
  }
};
