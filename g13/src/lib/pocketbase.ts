import { PUBLIC_POCKETBASE_URL } from '$env/static/public';
import PocketBase from 'pocketbase';
import type { TypedPocketBase } from './types/pocketbase';

export const createPocketBase = (): TypedPocketBase => {
  return new PocketBase(PUBLIC_POCKETBASE_URL) as unknown as TypedPocketBase;
};

export const pb = createPocketBase();
