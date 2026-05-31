import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const logs = await locals.pb.collection('activity_logs').getFullList({
      filter: `ticket = "${params.id}"`,
      sort: '-created',
      expand: 'actor'
    });
    return json(logs);
  } catch (e) {
    console.error('Failed to fetch activity logs:', e);
    throw error(500, 'Failed to fetch activity logs');
  }
};
