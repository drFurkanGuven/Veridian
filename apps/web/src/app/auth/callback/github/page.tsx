import { Suspense } from 'react';

import { OAuthCallbackClient } from '@/components/oauth-callback-client';

export default function GitHubCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-center text-ide-muted">Loading…</p>}>
      <OAuthCallbackClient provider="github" />
    </Suspense>
  );
}
