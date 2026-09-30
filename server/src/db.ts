import { DatabaseSync } from 'node:sqlite';

export type Role = 'member' | 'librarian' | 'admin';

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  created_at: string;
}

let db: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (!db) {
    const path = process.env.DB_PATH ?? 'lms.sqlite3';
    db = new DatabaseSync(path);
    db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
    `);
  }
  return db;
}

export function resetDb(): void {
  db?.close();
  db = null;
}

export function findUserByEmail(email: string): User | undefined {
  const row = getDb().prepare('SELECT * FROM users WHERE email = ?').get(email);
  return row as User | undefined;
}

export function createUser(name: string, email: string, role: Role = 'member'): User {
  getDb().prepare('INSERT INTO users (name, email, role) VALUES (?, ?, ?)').run(name, email, role);
  return findUserByEmail(email) as User;
}
