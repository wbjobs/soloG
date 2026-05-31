import { json, error } from '@sveltejs/kit';
import { updateTicketAssignee } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { assignee } = await request.json();
    const ticket = await updateTicketAssignee(locals.pb, params.id, assignee, locals.user);
    return json(ticket);
  } catch (e) {
    console.error('Failed to update ticket assignee:', e);
    throw error(500, 'Failed to update ticket assignee');
  }
};
