import { json, error } from '@sveltejs/kit';
import { createUploadSession, getUploadSession } from '$lib/server/uploadManager';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const { filename, size, ticketId } = await request.json();

    if (!filename || !size || !ticketId) {
      throw error(400, 'Missing required fields: filename, size, ticketId');
    }

    const session = await createUploadSession(filename, size, ticketId, locals.user.id);

    return json({
      id: session.id,
      offset: session.offset,
      size: session.size,
      uploadUrl: `/api/uploads/${session.id}`
    }, { status: 201 });
  } catch (e) {
    console.error('Failed to create upload session:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to create upload session');
  }
};

export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const sessionId = url.searchParams.get('sessionId');
    if (!sessionId) {
      throw error(400, 'Missing sessionId');
    }

    const session = await getUploadSession(sessionId);
    if (!session) {
      throw error(404, 'Upload session not found');
    }

    if (session.metadata.uploaderId !== locals.user.id) {
      throw error(403, 'Forbidden');
    }

    return json({
      id: session.id,
      offset: session.offset,
      size: session.size,
      filename: session.filename
    });
  } catch (e) {
    console.error('Failed to get upload session:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to get upload session');
  }
};
