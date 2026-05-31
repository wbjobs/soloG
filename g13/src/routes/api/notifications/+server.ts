import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const unreadOnly = url.searchParams.get('unread') === 'true';
    const page = parseInt(url.searchParams.get('page') || '1');
    const perPage = parseInt(url.searchParams.get('perPage') || '50');

    const filter = [`user = "${locals.user.id}"`];
    if (unreadOnly) {
      filter.push('read = false');
    }

    const notifications = await locals.pb.collection('notifications').getList(page, perPage, {
      sort: '-created',
      filter: filter.join(' && ')
    });

    return json(notifications);
  } catch (e) {
    console.error('Failed to fetch notifications:', e);
    throw error(500, 'Failed to fetch notifications');
  }
};

export const PATCH: RequestHandler = async ({ request, locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { ids, read } = await request.json();

    if (ids && ids.length > 0) {
      for (const id of ids) {
        await locals.pb.collection('notifications').update(id, { read });
      }
    } else {
      const unread = await locals.pb.collection('notifications').getFullList({
        filter: `user = "${locals.user.id}" && read = false`
      });
      for (const n of unread) {
        await locals.pb.collection('notifications').update(n.id, { read: true });
      }
    }

    return json({ success: true });
  } catch (e) {
    console.error('Failed to mark notifications:', e);
    throw error(500, 'Failed to mark notifications');
  }
};
