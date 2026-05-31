/// <reference types="@sveltejs/kit" />

import type { TypedPocketBase } from './lib/types/pocketbase';

declare global {
  namespace App {
    interface Locals {
      pb: TypedPocketBase;
      user: import('./lib/types/pocketbase').UsersRecord | null;
    }
  }
}

export {};
