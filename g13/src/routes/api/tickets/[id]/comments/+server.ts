import { json, error } from '@sveltejs/kit';
import { addComment } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { content, mentions } = await request.json();
    const comment = await addComment(locals.pb, params.id, content, mentions || [], locals.user);
    return json(comment);
  } catch (e) {
    console.error('Failed to add comment:', e);
    throw error(500, 'Failed to add comment');
  }
};

export const GET: RequestHandler = async ({ locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const comments = await locals.pb.collection('comments').getFullList({
      filter: `ticket = "${params.id}"`,
      sort: 'created',
      expand: 'author,mentions'
    });
    return json(comments);
  } catch (e) {
    console.error('Failed to fetch comments:', e);
    throw error(500, 'Failed to fetch comments');
  }
};
