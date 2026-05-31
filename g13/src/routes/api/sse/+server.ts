import { error } from '@sveltejs/kit';
import { sseManager } from '$lib/server/sseManager';

export const GET = async ({ locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const userId = locals.user.id;
  let clientId: string | null = null;

  const stream = new ReadableStream({
    start(controller) {
      clientId = sseManager.addClient(userId, (data) => {
        controller.enqueue(data);
      });

      controller.enqueue(`event: connected\ndata: ${JSON.stringify({ clientId })}\n\n`);

      const heartbeat = setInterval(() => {
        controller.enqueue(': heartbeat\n\n');
      }, 30000);

      (controller as unknown as { heartbeat: NodeJS.Timeout }).heartbeat = heartbeat;
    },
    cancel() {
      if (clientId) {
        sseManager.removeClient(userId, clientId);
      }
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no'
    }
  });
};
