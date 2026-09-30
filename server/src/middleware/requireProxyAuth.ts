import { Request, Response, NextFunction } from 'express';

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      authEmail?: string;
      authUser?: string;
    }
  }
}

/**
 * Only oauth2-proxy should ever be able to reach this app (it is the sole
 * upstream behind the proxy in docker-compose), so a request arriving here
 * without these headers means it bypassed the proxy and must be rejected.
 */
export function requireProxyAuth(req: Request, res: Response, next: NextFunction): void {
  const email = req.header('X-Forwarded-Email');
  if (!email) {
    res.status(401).json({ error: 'Missing authenticated identity. Sign in via /oauth2/start.' });
    return;
  }
  req.authEmail = email;
  req.authUser = req.header('X-Forwarded-User') ?? undefined;
  next();
}
