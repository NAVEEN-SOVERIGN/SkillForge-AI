import type { Response as ExpressResponse } from 'express';

const GITHUB_API_ORIGIN = 'https://api.github.com';
const inFlightRequests = new Map<string, Promise<Response>>();

export class GitHubRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'GitHubRequestError';
    this.status = status;
  }
}

export function isGitHubAuthEnabled(): boolean {
  return !!process.env.GITHUB_TOKEN?.trim();
}

export function logGitHubAuthStatus(): void {
  if (isGitHubAuthEnabled()) {
    console.log('GitHub auth: enabled');
    return;
  }
  console.warn('GITHUB_TOKEN not set: limited to 60 requests/hour');
  console.log('GitHub auth: disabled');
}

function rateLimitMessage(response: Response): string {
  const reset = Number(response.headers.get('x-ratelimit-reset'));
  const retryAt = Number.isFinite(reset) && reset > 0
    ? new Date(reset * 1000).toISOString()
    : 'later';
  return `GitHub rate limit reached, try again at ${retryAt}`;
}

function toGitHubUrl(target: string): URL {
  let url: URL;
  try {
    url = new URL(target, GITHUB_API_ORIGIN);
  } catch {
    throw new GitHubRequestError('A valid GitHub API path is required.', 400);
  }
  if (url.origin !== GITHUB_API_ORIGIN) {
    throw new GitHubRequestError('Only GitHub API requests are supported.', 400);
  }
  return url;
}

/**
 * Single entry point for every api.github.com request. The token is read from
 * the server environment on each call and is never returned to the client.
 */
export async function githubFetch(target: string, init: RequestInit = {}): Promise<Response> {
  const url = toGitHubUrl(target);
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/vnd.github+json');
  headers.set('X-GitHub-Api-Version', '2022-11-28');
  headers.set('User-Agent', 'SkillForge-AI');
  const token = process.env.GITHUB_TOKEN?.trim();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  else headers.delete('Authorization');

  let response: Response;
  const inFlightKey = url.toString();
  const existingFlight = inFlightRequests.get(inFlightKey);
  if (existingFlight) {
    try {
      const cloned = (await existingFlight).clone();
      return cloned;
    } catch {
      // If the in-flight failed, proceed to fresh attempt
    }
  }

  const flightPromise = (async () => {
    try {
      return await fetch(url, { ...init, headers, signal: init.signal ?? AbortSignal.timeout(12_000) });
    } finally {
      inFlightRequests.delete(inFlightKey);
    }
  })();
  inFlightRequests.set(inFlightKey, flightPromise);

  try {
    response = await flightPromise;
  } catch {
    throw new GitHubRequestError('Could not reach GitHub. Check your connection and try again.', 502);
  }

  if (!response.ok) {
    if (response.status === 401) throw new GitHubRequestError('GitHub token invalid or expired', 401);
    if (response.status === 403 || response.status === 429) throw new GitHubRequestError(rateLimitMessage(response), response.status);
    if (response.status === 404) throw new GitHubRequestError('Repository, pull request, or file was not found on GitHub.', 404);
    throw new GitHubRequestError(`GitHub request failed (${response.status}). Try again shortly.`, response.status);
  }
  return response;
}

export function sendGitHubError(res: ExpressResponse, error: unknown): void {
  if (error instanceof GitHubRequestError) {
    res.status(error.status).json({ error: error.message });
    return;
  }
  console.warn('GitHub request failed:', error instanceof Error ? error.message : 'unknown error');
  res.status(502).json({ error: 'Could not reach GitHub. Check your connection and try again.' });
}
