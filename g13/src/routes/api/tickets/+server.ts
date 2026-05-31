import { json, error } from '@sveltejs/kit';
import { createTicket } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const data = await request.json();
    const ticket = await createTicket(locals.pb, data, locals.user);
    return json(ticket);
  } catch (e) {
    console.error('Failed to create ticket:', e);
    throw error(500, 'Failed to create ticket');
  }
};

export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const status = url.searchParams.get('status');
    const assignee = url.searchParams.get('assignee');
    const page = parseInt(url.searchParams.get('page') || '1');
    const perPage = parseInt(url.searchParams.get('perPage') || '20');

    const filter = [];
    if (status) filter.push(`status = "${status}"`);
    if (assignee) filter.push(`assignee = "${assignee}"`);

    const tickets = await locals.pb.collection('tickets').getList(page, perPage, {
      sort: '-created',
      expand: 'creator,assignee',
      filter: filter.length > 0 ? filter.join(' && ') : undefined
    });

    return json(tickets);
  } catch (e) {
    console.error('Failed to fetch tickets:', e);
    throw error(500, 'Failed to fetch tickets');
  }
};
