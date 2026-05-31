import { json, error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, locals }) => {
  const { email, password } = await request.json();

  try {
    await locals.pb.collection('users').authWithPassword(email, password);
    return json({ success: true, user: locals.pb.authStore.model });
  } catch (e) {
    console.error('Login failed:', e);
    throw error(401, '邮箱或密码错误');
  }
};
