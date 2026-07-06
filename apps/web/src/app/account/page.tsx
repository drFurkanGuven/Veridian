'use client';

import type { User, UserSession } from '@veridian/shared-types';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  changePassword,
  getCurrentUser,
  listSessions,
  revokeOtherSessions,
  revokeSession,
  updateProfile,
} from '@/lib/account-api';
import { isLoggedIn } from '@/lib/projects-api';

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [displayName, setDisplayName] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login');
      return;
    }
    load().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load account');
    });
  }, [router]);

  async function load() {
    const [me, sessionItems] = await Promise.all([getCurrentUser(), listSessions()]);
    setUser(me);
    setDisplayName(me.displayName);
    setSessions(sessionItems);
  }

  async function handleProfileSave() {
    setError('');
    setMessage('');
    try {
      const updated = await updateProfile({ displayName });
      setUser(updated);
      setMessage('Profile updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile');
    }
  }

  async function handlePasswordChange() {
    setError('');
    setMessage('');
    try {
      await changePassword({ currentPassword, newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setMessage('Password changed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change password');
    }
  }

  async function handleRevokeSession(sessionId: string) {
    setError('');
    try {
      await revokeSession(sessionId);
      await load();
      setMessage('Session revoked');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke session');
    }
  }

  async function handleRevokeOthers() {
    setError('');
    try {
      const count = await revokeOtherSessions();
      await load();
      setMessage(`Revoked ${count} other session(s)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke sessions');
    }
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center text-ide-muted">
        Loading account…
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl space-y-8 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Account</h1>
          <p className="text-sm text-ide-muted">{user.email}</p>
        </div>
        <div className="flex gap-4 text-sm">
          {user.role === 'admin' && (
            <Link href="/admin" className="text-emerald-400 underline hover:text-emerald-300">
              Admin panel
            </Link>
          )}
          <Link href="/projects" className="text-ide-muted underline">
            Back to projects
          </Link>
        </div>
      </header>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {message && <p className="text-sm text-green-400">{message}</p>}

      <section className="rounded border border-ide-border p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase text-ide-muted">Profile</h2>
        <div className="space-y-3">
          <p className="text-sm text-ide-muted">
            Role: <span className="text-white">{user.role}</span> · Status:{' '}
            <span className={user.isActive ? 'text-green-400' : 'text-red-400'}>
              {user.isActive ? 'active' : 'disabled'}
            </span>
          </p>
          <label className="block text-sm text-ide-muted">
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-white"
            />
          </label>
          <button
            type="button"
            onClick={handleProfileSave}
            className="rounded bg-white px-3 py-1 text-sm font-medium text-black"
          >
            Save profile
          </button>
        </div>
      </section>

      <section className="rounded border border-ide-border p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase text-ide-muted">Password</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="rounded border border-ide-border bg-ide-bg px-3 py-2 text-white"
          />
          <input
            type="password"
            placeholder="New password (letter + digit)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="rounded border border-ide-border bg-ide-bg px-3 py-2 text-white"
          />
        </div>
        <button
          type="button"
          onClick={handlePasswordChange}
          className="mt-3 rounded border border-ide-border px-3 py-1 text-sm hover:bg-ide-sidebar"
        >
          Change password
        </button>
      </section>

      <section className="rounded border border-ide-border p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase text-ide-muted">Sessions</h2>
          <button
            type="button"
            onClick={handleRevokeOthers}
            className="text-xs text-red-400 underline"
          >
            Revoke other sessions
          </button>
        </div>
        <ul className="space-y-2 text-sm">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex items-start justify-between rounded border border-ide-border px-3 py-2"
            >
              <div className="text-ide-muted">
                <p>{session.userAgent ?? 'Unknown device'}</p>
                <p className="text-xs">{session.ipAddress ?? 'unknown IP'}</p>
                <p className="text-xs">
                  Created {new Date(session.createdAt).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRevokeSession(session.id)}
                className="text-xs text-red-400 underline"
              >
                Revoke
              </button>
            </li>
          ))}
          {sessions.length === 0 && <li className="text-ide-muted">No active sessions</li>}
        </ul>
      </section>
    </main>
  );
}
