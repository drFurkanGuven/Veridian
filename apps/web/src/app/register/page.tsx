'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { OAuthButtons } from '@/components/oauth-buttons';
import { registerUser, saveAuthTokens } from '@/lib/auth-api';

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await registerUser({ email, password, displayName });
      saveAuthTokens(result.tokens);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-ide-border bg-ide-sidebar p-8">
        <header className="space-y-2 text-center">
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
          <p className="text-sm text-ide-muted">Start building FPGA projects in the cloud</p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block space-y-1 text-sm">
            <span className="text-ide-muted">Display name</span>
            <input
              type="text"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-ide-text"
            />
          </label>
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
            <span className="text-ide-muted">Password (min 8 characters)</span>
            <input
              type="password"
              required
              minLength={8}
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
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <OAuthButtons onError={setError} />

        <p className="text-center text-sm text-ide-muted">
          Already have an account?{' '}
          <Link href="/login" className="text-white underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
