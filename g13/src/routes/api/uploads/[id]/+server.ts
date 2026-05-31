import { json, error } from '@sveltejs/kit';
import { getUploadSession, uploadChunk, completeUpload } from '$lib/server/uploadManager';
import fs from 'fs/promises';
import { PUBLIC_POCKETBASE_URL } from '$env/static/public';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const session = await getUploadSession(params.id);
    if (!session) {
      throw error(404, 'Upload session not found');
    }

    if (session.metadata.uploaderId !== locals.user.id) {
      throw error(403, 'Forbidden');
    }

    const uploadOffsetHeader = request.headers.get('upload-offset');
    const contentLength = request.headers.get('content-length');

    if (!uploadOffsetHeader) {
      throw error(400, 'Missing Upload-Offset header');
    }

    const clientOffset = parseInt(uploadOffsetHeader, 10);
    if (isNaN(clientOffset)) {
      throw error(400, 'Invalid Upload-Offset header');
    }

    if (clientOffset !== session.offset) {
      return new Response(null, {
        status: 409,
        headers: {
          'Upload-Offset': String(session.offset),
          'Upload-Length': String(session.size)
        }
      });
    }

    const arrayBuffer = await request.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const newOffset = await uploadChunk(params.id, buffer, clientOffset);

    return new Response(null, {
      status: 204,
      headers: {
        'Upload-Offset': String(newOffset),
        'Upload-Length': String(session.size)
      }
    });
  } catch (e) {
    console.error('Failed to upload chunk:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to upload chunk');
  }
};

export const POST: RequestHandler = async ({ request, locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const session = await getUploadSession(params.id);
    if (!session) {
      throw error(404, 'Upload session not found');
    }

    if (session.metadata.uploaderId !== locals.user.id) {
      throw error(403, 'Forbidden');
    }

    const finalPath = await completeUpload(params.id);

    const fileBuffer = await fs.readFile(finalPath);
    const blob = new Blob([fileBuffer], { type: 'application/octet-stream' });
    const file = new File([blob], session.filename, { type: 'application/octet-stream' });

    const formData = new FormData();
    formData.append('ticket', session.metadata.ticketId);
    formData.append('uploader', session.metadata.uploaderId);
    formData.append('filename', session.filename);
    formData.append('size', String(session.size));
    formData.append('file', file);

    const pbResponse = await fetch(`${PUBLIC_POCKETBASE_URL}/api/collections/attachments/records`, {
      method: 'POST',
      headers: {
        'Authorization': locals.pb.authStore.token ? `Bearer ${locals.pb.authStore.token}` : ''
      },
      body: formData
    });

    if (!pbResponse.ok) {
      const errorData = await pbResponse.json().catch(() => ({}));
      console.error('PocketBase error:', errorData);
      throw error(500, 'Failed to save attachment to database');
    }

    const attachment = await pbResponse.json();

    await fs.unlink(finalPath).catch(() => {});

    return json(attachment, { status: 201 });
  } catch (e) {
    console.error('Failed to complete upload:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to complete upload');
  }
};

export const HEAD: RequestHandler = async ({ locals, params }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  try {
    const session = await getUploadSession(params.id);
    if (!session) {
      throw error(404, 'Upload session not found');
    }

    if (session.metadata.uploaderId !== locals.user.id) {
      throw error(403, 'Forbidden');
    }

    return new Response(null, {
      status: 200,
      headers: {
        'Upload-Offset': String(session.offset),
        'Upload-Length': String(session.size),
        'Cache-Control': 'no-store'
      }
    });
  } catch (e) {
    console.error('Failed to get upload status:', e);
    if (e instanceof Error && e.name === 'HttpError') {
      throw e;
    }
    throw error(500, 'Failed to get upload status');
  }
};
