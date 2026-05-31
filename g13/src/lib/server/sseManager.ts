import type { NotificationsRecord } from '$lib/types/pocketbase';

interface SSEClient {
  id: string;
  userId: string;
  enqueue: (data: string) => void;
}

const clients = new Map<string, SSEClient[]>();

export const sseManager = {
  addClient(userId: string, enqueue: (data: string) => void): string {
    const clientId = crypto.randomUUID();
    const client: SSEClient = { id: clientId, userId, enqueue };

    if (!clients.has(userId)) {
      clients.set(userId, []);
    }
    clients.get(userId)!.push(client);

    console.log(`[SSE] Client connected: ${clientId} for user ${userId}`);
    return clientId;
  },

  removeClient(userId: string, clientId: string): void {
    const userClients = clients.get(userId);
    if (userClients) {
      const index = userClients.findIndex((c) => c.id === clientId);
      if (index !== -1) {
        userClients.splice(index, 1);
        console.log(`[SSE] Client disconnected: ${clientId}`);
      }
      if (userClients.length === 0) {
        clients.delete(userId);
      }
    }
  },

  sendToUser(userId: string, data: NotificationsRecord & { ticket_title: string }): void {
    const userClients = clients.get(userId);
    if (userClients && userClients.length > 0) {
      const message = `data: ${JSON.stringify(data)}\n\n`;
      for (const client of userClients) {
        try {
          client.enqueue(message);
        } catch (e) {
          console.error(`[SSE] Failed to send to client ${client.id}:`, e);
        }
      }
      console.log(`[SSE] Sent notification to ${userClients.length} clients for user ${userId}`);
    }
  },

  broadcast(userIds: string[], data: NotificationsRecord & { ticket_title: string }): void {
    for (const userId of userIds) {
      this.sendToUser(userId, data);
    }
  },

  getConnectedUsers(): string[] {
    return Array.from(clients.keys());
  }
};
