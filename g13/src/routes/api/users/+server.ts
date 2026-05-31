import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const search = url.searchParams.get('search');
    const filter = search ? `name ~ "${search}" || email ~ "${search}"` : undefined;

    const users = await locals.pb.collection('users').getFullList({
      filter,
      sort: 'name'
    });
    return json(users);
  } catch (e) {
    console.error('Failed to fetch users:', e);
    throw error(500, 'Failed to fetch users');
  }
};
