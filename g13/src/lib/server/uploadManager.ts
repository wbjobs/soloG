import fs from 'fs/promises';
import path from 'path';
import { randomUUID } from 'crypto';

export interface UploadSession {
  id: string;
  filename: string;
  size: number;
  offset: number;
  uploadDir: string;
  metadata: {
    ticketId: string;
    uploaderId: string;
  };
  createdAt: number;
}

const UPLOAD_DIR = path.join(process.cwd(), 'uploads');
const SESSION_FILE = path.join(UPLOAD_DIR, 'sessions.json');

const ensureDir = async () => {
  try {
    await fs.access(UPLOAD_DIR);
  } catch {
    await fs.mkdir(UPLOAD_DIR, { recursive: true });
  }
};

const loadSessions = async (): Promise<Record<string, UploadSession>> => {
  await ensureDir();
  try {
    const data = await fs.readFile(SESSION_FILE, 'utf-8');
    return JSON.parse(data);
  } catch {
    return {};
  }
};

const saveSessions = async (sessions: Record<string, UploadSession>) => {
  await ensureDir();
  await fs.writeFile(SESSION_FILE, JSON.stringify(sessions, null, 2));
};

export const createUploadSession = async (
  filename: string,
  size: number,
  ticketId: string,
  uploaderId: string
): Promise<UploadSession> => {
  const sessions = await loadSessions();
  const id = randomUUID();
  const uploadDir = path.join(UPLOAD_DIR, id);

  await fs.mkdir(uploadDir, { recursive: true });

  const session: UploadSession = {
    id,
    filename,
    size,
    offset: 0,
    uploadDir,
    metadata: {
      ticketId,
      uploaderId
    },
    createdAt: Date.now()
  };

  sessions[id] = session;
  await saveSessions(sessions);

  return session;
};

export const getUploadSession = async (id: string): Promise<UploadSession | null> => {
  const sessions = await loadSessions();
  return sessions[id] || null;
};

export const uploadChunk = async (
  sessionId: string,
  chunk: Buffer,
  offset: number
): Promise<number> => {
  const sessions = await loadSessions();
  const session = sessions[sessionId];

  if (!session) {
    throw new Error('Upload session not found');
  }

  if (offset !== session.offset) {
    throw new Error(`Invalid offset. Expected ${session.offset}, got ${offset}`);
  }

  const chunkPath = path.join(session.uploadDir, `chunk-${offset.toString().padStart(10, '0')}`);
  await fs.writeFile(chunkPath, chunk);

  session.offset += chunk.length;
  sessions[sessionId] = session;
  await saveSessions(sessions);

  return session.offset;
};

export const completeUpload = async (sessionId: string): Promise<string> => {
  const sessions = await loadSessions();
  const session = sessions[sessionId];

  if (!session) {
    throw new Error('Upload session not found');
  }

  if (session.offset !== session.size) {
    throw new Error(`Upload incomplete. Expected ${session.size} bytes, got ${session.offset}`);
  }

  const finalPath = path.join(session.uploadDir, session.filename);

  const chunkDir = session.uploadDir;
  const files = await fs.readdir(chunkDir);
  const chunkFiles = files
    .filter((f) => f.startsWith('chunk-'))
    .sort((a, b) => a.localeCompare(b));

  const writeStream = (await import('fs')).createWriteStream(finalPath);

  for (const chunkFile of chunkFiles) {
    const chunkPath = path.join(chunkDir, chunkFile);
    const chunkData = await fs.readFile(chunkPath);
    await new Promise<void>((resolve, reject) => {
      writeStream.write(chunkData, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
    await fs.unlink(chunkPath);
  }

  await new Promise<void>((resolve) => writeStream.end(() => resolve()));

  delete sessions[sessionId];
  await saveSessions(sessions);

  return finalPath;
};

export const cleanupExpiredSessions = async () => {
  const sessions = await loadSessions();
  const now = Date.now();
  const expired: string[] = [];

  for (const [id, session] of Object.entries(sessions)) {
    if (now - session.createdAt > 24 * 60 * 60 * 1000) {
      expired.push(id);
      try {
        await fs.rm(session.uploadDir, { recursive: true, force: true });
      } catch (e) {
        console.error('Failed to cleanup session:', id, e);
      }
    }
  }

  for (const id of expired) {
    delete sessions[id];
  }

  if (expired.length > 0) {
    await saveSessions(sessions);
    console.log(`Cleaned up ${expired.length} expired upload sessions`);
  }
};
