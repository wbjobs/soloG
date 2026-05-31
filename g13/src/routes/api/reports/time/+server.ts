import { json, error } from '@sveltejs/kit';
import { getTimeReport } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const startDate = url.searchParams.get('startDate');
    const endDate = url.searchParams.get('endDate');
    const userId = url.searchParams.get('userId') || undefined;

    if (!startDate || !endDate) {
      throw error(400, 'Missing startDate or endDate');
    }

    const report = await getTimeReport(locals.pb, startDate, endDate, userId);
    return json(report);
  } catch (e) {
    console.error('Failed to generate time report:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to generate time report');
  }
};
