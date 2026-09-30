import request from 'supertest';
import express from 'express';
import { resetDb } from '../../db';
import authRouter from '../auth';

function buildApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/auth', authRouter);
  return app;
}

describe('auth routes', () => {
  beforeEach(() => {
    process.env.DB_PATH = ':memory:';
    resetDb();
  });

  afterAll(() => {
    resetDb();
  });

  it('rejects requests with no forwarded-auth headers', async () => {
    const app = buildApp();
    const res = await request(app).get('/api/auth/session');
    expect(res.status).toBe(401);
  });

  it('reports needsRegistration for a first-time authenticated email', async () => {
    const app = buildApp();
    const res = await request(app)
      .get('/api/auth/session')
      .set('X-Forwarded-Email', 'new.user@example.com');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ needsRegistration: true, email: 'new.user@example.com' });
  });

  it('registers a new profile for an authenticated email', async () => {
    const app = buildApp();
    const res = await request(app)
      .post('/api/auth/register')
      .set('X-Forwarded-Email', 'new.user@example.com')
      .send({ name: 'New User' });
    expect(res.status).toBe(201);
    expect(res.body.user).toEqual({ name: 'New User', email: 'new.user@example.com', role: 'member' });
  });

  it('rejects registering the same email twice', async () => {
    const app = buildApp();
    await request(app)
      .post('/api/auth/register')
      .set('X-Forwarded-Email', 'dup@example.com')
      .send({ name: 'First' });

    const res = await request(app)
      .post('/api/auth/register')
      .set('X-Forwarded-Email', 'dup@example.com')
      .send({ name: 'Second' });

    expect(res.status).toBe(409);
  });

  it('returns the existing profile for an already-registered email', async () => {
    const app = buildApp();
    await request(app)
      .post('/api/auth/register')
      .set('X-Forwarded-Email', 'existing@example.com')
      .send({ name: 'Existing User' });

    const res = await request(app)
      .get('/api/auth/session')
      .set('X-Forwarded-Email', 'existing@example.com');

    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      needsRegistration: false,
      user: { name: 'Existing User', email: 'existing@example.com', role: 'member' },
    });
  });
});
