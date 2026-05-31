import { json, error } from '@sveltejs/kit';
import { addTimeLog, getTicketTimeLogs } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { hours, description, log_date } = await request.json();

    if (!hours || hours <= 0) {
      throw error(400, 'Invalid hours');
    }

    const timeLog = await addTimeLog(
      locals.pb,
      params.id,
      hours,
      description || '',
      log_date || new Date().toISOString().split('T')[0],
      locals.user
    );

    return json(timeLog, { status: 201 });
  } catch (e) {
    console.error('Failed to add time log:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to add time log');
  }
};

export const GET: RequestHandler = async ({ locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const logs = await getTicketTimeLogs(locals.pb, params.id);
    return json(logs);
  } catch (e) {
    console.error('Failed to fetch time logs:', e);
    throw error(500, 'Failed to fetch time logs');
  }
};
