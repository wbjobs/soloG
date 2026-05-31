import { json, error } from '@sveltejs/kit';
import { updateTicketStatus } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { status } = await request.json();
    const ticket = await updateTicketStatus(locals.pb, params.id, status, locals.user);
    return json(ticket);
  } catch (e) {
    console.error('Failed to update ticket status:', e);
    throw error(500, 'Failed to update ticket status');
  }
};
