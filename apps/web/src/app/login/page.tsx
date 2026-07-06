'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { getOAuthUrl, loginUser, saveAuthTokens } from '@/lib/auth-api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await loginUser({ email, password });
      saveAuthTokens(result.tokens);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleOAuth(provider: 'google' | 'github') {
    setError(null);
    try {
      const { url, state } = await getOAuthUrl(provider);
      sessionStorage.setItem(`veridian_oauth_state_${provider}`, state);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OAuth unavailable');
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-ide-border bg-ide-sidebar p-8">
        <header className="space-y-2 text-center">
          <h1 className="text-2xl font-bold text-white">Sign in to Veridian</h1>
          <p className="text-sm text-ide-muted">Email, Google, or GitHub</p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block space-y-1 text-sm">
            <span className="text-ide-muted">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-ide-text"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-ide-muted">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-ide-text"
            />
          </label>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-white px-4 py-2 font-medium text-black disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => handleOAuth('google')}
            className="flex-1 rounded border border-ide-border px-4 py-2 text-sm hover:bg-ide-bg"
          >
            Google
          </button>
          <button
            type="button"
            onClick={() => handleOAuth('github')}
            className="flex-1 rounded border border-ide-border px-4 py-2 text-sm hover:bg-ide-bg"
          >
            GitHub
          </button>
        </div>

        <p className="text-center text-sm text-ide-muted">
          No account?{' '}
          <Link href="/register" className="text-white underline">
            Register
          </Link>
        </p>
      </div>
    </main>
  );
}
