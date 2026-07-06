'use client';

import type { OAuthProvidersResponse } from '@veridian/shared-types';
import { useEffect, useState } from 'react';

import { getAuthProviders, getOAuthUrl, oauthStateKey } from '@/lib/auth-api';

interface OAuthButtonsProps {
  onError: (message: string) => void;
}

export function OAuthButtons({ onError }: OAuthButtonsProps) {
  const [providers, setProviders] = useState<OAuthProvidersResponse | null>(null);

  useEffect(() => {
    getAuthProviders()
      .then(setProviders)
      .catch(() => setProviders({ google: false, github: false }));
  }, []);

  async function handleOAuth(provider: 'google' | 'github') {
    onError('');
    try {
      const { url, state } = await getOAuthUrl(provider);
      sessionStorage.setItem(oauthStateKey(provider), state);
      window.location.href = url;
    } catch (err) {
      onError(err instanceof Error ? err.message : 'OAuth unavailable');
    }
  }

  if (!providers?.google && !providers?.github) {
    return (
      <p className="text-center text-xs text-ide-muted">
        Google/GitHub sign-in is not configured on this server.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        {providers.google && (
          <button
            type="button"
            onClick={() => handleOAuth('google')}
            className="flex-1 rounded border border-ide-border px-4 py-2 text-sm hover:bg-ide-bg"
          >
            Google
          </button>
        )}
        {providers.github && (
          <button
            type="button"
            onClick={() => handleOAuth('github')}
            className="flex-1 rounded border border-ide-border px-4 py-2 text-sm hover:bg-ide-bg"
          >
            GitHub
          </button>
        )}
      </div>
    </div>
  );
}
