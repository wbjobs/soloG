import type { Handle } from '@sveltejs/kit';
import { createPocketBase } from '$lib/pocketbase';
import { building } from '$app/environment';

export const handle: Handle = async ({ event, resolve }) => {
  if (building) {
    return resolve(event);
  }

  event.locals.pb = createPocketBase();

  event.locals.pb.authStore.loadFromCookie(event.request.headers.get('cookie') || '');

  try {
    if (event.locals.pb.authStore.isValid) {
      await event.locals.pb.collection('users').authRefresh();
      event.locals.user = event.locals.pb.authStore.model;
    }
  } catch (_) {
    event.locals.pb.authStore.clear();
    event.locals.user = null;
  }

  const response = await resolve(event);

  response.headers.set(
    'set-cookie',
    event.locals.pb.authStore.exportToCookie({ httpOnly: false, secure: false })
  );

  return response;
};
