'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { completeOAuthCallback, oauthStateKey, saveAuthTokens } from '@/lib/auth-api';

export function OAuthCallbackClient({ provider }: { provider: 'google' | 'github' }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const savedState = sessionStorage.getItem(oauthStateKey(provider));

    if (!code || !state) {
      setError('Missing OAuth code from provider.');
      return;
    }
    if (!savedState || savedState !== state) {
      setError('Invalid OAuth state. Please try again.');
      return;
    }

    completeOAuthCallback(provider, code, state)
      .then((result) => {
        sessionStorage.removeItem(oauthStateKey(provider));
        saveAuthTokens(result.tokens);
        router.replace('/projects');
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'OAuth sign-in failed');
      });
  }, [provider, router, searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="rounded-lg border border-ide-border bg-ide-sidebar p-8 text-center">
        {error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : (
          <p className="text-sm text-ide-muted">Completing {provider} sign-in…</p>
        )}
      </div>
    </main>
  );
}
