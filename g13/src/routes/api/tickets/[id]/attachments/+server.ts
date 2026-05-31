import { json, error } from '@sveltejs/kit';
import { addAttachment } from '$lib/server/ticketService';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      throw error(400, 'No file provided');
    }

    const attachment = await addAttachment(locals.pb, params.id, file, locals.user);
    return json(attachment);
  } catch (e) {
    console.error('Failed to upload attachment:', e);
    throw error(500, 'Failed to upload attachment');
  }
};

export const GET: RequestHandler = async ({ locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const attachments = await locals.pb.collection('attachments').getFullList({
      filter: `ticket = "${params.id}"`,
      sort: '-created',
      expand: 'uploader'
    });
    return json(attachments);
  } catch (e) {
    console.error('Failed to fetch attachments:', e);
    throw error(500, 'Failed to fetch attachments');
  }
};
