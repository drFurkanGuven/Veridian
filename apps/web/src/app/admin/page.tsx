'use client';

import type { AdminUser, AuditEventType, AuditLogEntry } from '@veridian/shared-types';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { getCurrentUser } from '@/lib/account-api';
import {
  AUDIT_EVENT_TYPES,
  listAdminUsers,
  listAuditLogs,
  updateAdminUser,
  USER_ROLES,
} from '@/lib/admin-api';
import { isLoggedIn } from '@/lib/projects-api';

type Tab = 'users' | 'audit';

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

export default function AdminPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('users');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userPage, setUserPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [userHasMore, setUserHasMore] = useState(false);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditHasMore, setAuditHasMore] = useState(false);
  const [eventFilter, setEventFilter] = useState<AuditEventType | ''>('');

  const loadUsers = useCallback(async () => {
    const data = await listAdminUsers(userPage, 20, search);
    setUsers(data.items);
    setUserTotal(data.total);
    setUserHasMore(data.hasMore);
  }, [userPage, search]);

  const loadAudit = useCallback(async () => {
    const data = await listAuditLogs({
      page: auditPage,
      pageSize: 50,
      eventType: eventFilter || undefined,
    });
    setLogs(data.items);
    setAuditTotal(data.total);
    setAuditHasMore(data.hasMore);
  }, [auditPage, eventFilter]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login');
      return;
    }
    getCurrentUser()
      .then((user) => {
        if (user.role !== 'admin') {
          router.replace('/projects');
        }
      })
      .catch(() => router.replace('/login'));
  }, [router]);

  useEffect(() => {
    if (tab !== 'users') return;
    loadUsers().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    });
  }, [tab, loadUsers]);

  useEffect(() => {
    if (tab !== 'audit') return;
    loadAudit().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load audit log');
    });
  }, [tab, loadAudit]);

  async function handleToggleActive(user: AdminUser) {
    setError('');
    setMessage('');
    try {
      await updateAdminUser(user.id, { isActive: !user.isActive });
      setMessage(`${user.email} ${user.isActive ? 'disabled' : 'enabled'}`);
      await loadUsers();
      if (tab === 'audit') await loadAudit();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    }
  }

  async function handleRoleChange(user: AdminUser, role: AdminUser['role']) {
    if (user.role === role) return;
    setError('');
    setMessage('');
    try {
      await updateAdminUser(user.id, { role });
      setMessage(`${user.email} role set to ${role}`);
      await loadUsers();
      if (tab === 'audit') await loadAudit();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role');
    }
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setUserPage(1);
    setSearch(searchInput.trim());
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl space-y-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin</h1>
          <p className="text-sm text-ide-muted">User management and audit trail</p>
        </div>
        <div className="flex gap-4 text-sm">
          <Link href="/account" className="text-ide-muted underline hover:text-white">
            Account
          </Link>
          <Link href="/projects" className="text-ide-muted underline hover:text-white">
            Projects
          </Link>
        </div>
      </header>

      <div className="flex gap-2 border-b border-ide-border pb-2">
        <button
          type="button"
          onClick={() => setTab('users')}
          className={`rounded px-3 py-1 text-sm ${
            tab === 'users' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
          }`}
        >
          Users ({userTotal || users.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('audit')}
          className={`rounded px-3 py-1 text-sm ${
            tab === 'audit' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
          }`}
        >
          Audit log ({auditTotal || logs.length})
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {message && <p className="text-sm text-green-400">{message}</p>}

      {tab === 'users' && (
        <section className="space-y-4">
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search email or name…"
              className="flex-1 rounded border border-ide-border bg-ide-bg px-3 py-2 text-sm text-white"
            />
            <button
              type="submit"
              className="rounded border border-ide-border px-4 py-2 text-sm hover:bg-ide-sidebar"
            >
              Search
            </button>
          </form>

          <div className="overflow-x-auto rounded border border-ide-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-ide-border bg-ide-sidebar text-xs uppercase text-ide-muted">
                <tr>
                  <th className="px-3 py-2">User</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Security</th>
                  <th className="px-3 py-2">Last login</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-ide-border/50">
                    <td className="px-3 py-3">
                      <p className="font-medium text-white">{user.displayName}</p>
                      <p className="text-xs text-ide-muted">{user.email}</p>
                    </td>
                    <td className="px-3 py-3">
                      <select
                        value={user.role}
                        onChange={(e) =>
                          handleRoleChange(user, e.target.value as AdminUser['role'])
                        }
                        className="rounded border border-ide-border bg-ide-bg px-2 py-1 text-xs text-white"
                      >
                        {USER_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={
                          user.isActive ? 'text-green-400' : 'text-red-400'
                        }
                      >
                        {user.isActive ? 'active' : 'disabled'}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-xs text-ide-muted">
                      <p>Failed: {user.failedLoginAttempts}</p>
                      <p>Locked: {formatDate(user.lockedUntil)}</p>
                    </td>
                    <td className="px-3 py-3 text-xs text-ide-muted">
                      {formatDate(user.lastLoginAt)}
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => handleToggleActive(user)}
                        className="text-xs text-red-400 underline"
                      >
                        {user.isActive ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-ide-muted">
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-ide-muted">
            <span>
              Page {userPage} · {userTotal} total
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={userPage <= 1}
                onClick={() => setUserPage((p) => p - 1)}
                className="rounded border border-ide-border px-3 py-1 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!userHasMore}
                onClick={() => setUserPage((p) => p + 1)}
                className="rounded border border-ide-border px-3 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      )}

      {tab === 'audit' && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-ide-muted">
              Event
              <select
                value={eventFilter}
                onChange={(e) => {
                  setAuditPage(1);
                  setEventFilter(e.target.value as AuditEventType | '');
                }}
                className="ml-2 rounded border border-ide-border bg-ide-bg px-2 py-1 text-sm text-white"
              >
                <option value="">All events</option>
                {AUDIT_EVENT_TYPES.map((event) => (
                  <option key={event} value={event}>
                    {event}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="overflow-x-auto rounded border border-ide-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-ide-border bg-ide-sidebar text-xs uppercase text-ide-muted">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Event</th>
                  <th className="px-3 py-2">Actor</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">IP</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-ide-border/50 align-top">
                    <td className="px-3 py-2 text-ide-muted">
                      {formatDate(log.createdAt)}
                    </td>
                    <td className="px-3 py-2 text-white">{log.eventType}</td>
                    <td className="px-3 py-2 text-ide-muted">{log.userId ?? '—'}</td>
                    <td className="px-3 py-2 text-ide-muted">{log.targetUserId ?? '—'}</td>
                    <td className="px-3 py-2 text-ide-muted">{log.ipAddress ?? '—'}</td>
                    <td className="max-w-xs truncate px-3 py-2 text-ide-muted">
                      {log.metadata ? JSON.stringify(log.metadata) : '—'}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-ide-muted">
                      No audit events
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-ide-muted">
            <span>
              Page {auditPage} · {auditTotal} total
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={auditPage <= 1}
                onClick={() => setAuditPage((p) => p - 1)}
                className="rounded border border-ide-border px-3 py-1 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!auditHasMore}
                onClick={() => setAuditPage((p) => p + 1)}
                className="rounded border border-ide-border px-3 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
