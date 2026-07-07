'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';

import type { Project } from '@veridian/shared-types';

import { createProject, deleteProject, isLoggedIn, listProjects } from '@/lib/projects-api';
import { getCurrentUser } from '@/lib/account-api';

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await listProjects();
      setProjects(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login');
      return;
    }
    load();
    getCurrentUser()
      .then((user) => setIsAdmin(user.role === 'admin'))
      .catch(() => undefined);
  }, [router]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setError('');
    try {
      await createProject({ name: name.trim() });
      setName('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
  }

  async function handleDelete(projectId: string) {
    setError('');
    try {
      await deleteProject(projectId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-sm text-ide-muted">Your FPGA workspaces</p>
        </div>
        <div className="flex gap-4">
          {isAdmin && (
            <Link href="/admin" className="text-sm text-emerald-400 underline hover:text-emerald-300">
              Admin
            </Link>
          )}
          <Link href="/account" className="text-sm text-ide-muted underline hover:text-white">
            Account
          </Link>
        </div>
      </header>

      <form onSubmit={handleCreate} className="mb-8 flex gap-3">
        <input
          type="text"
          placeholder="New project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded border border-ide-border bg-ide-sidebar px-3 py-2 text-ide-text"
        />
        <button
          type="submit"
          className="rounded bg-white px-4 py-2 font-medium text-black"
        >
          Create
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {loading ? (
        <p className="text-ide-muted">Loading…</p>
      ) : projects.length === 0 ? (
        <p className="text-ide-muted">No projects yet. Create your first one above.</p>
      ) : (
        <ul className="space-y-3">
          {projects.map((project) => (
            <li
              key={project.id}
              className="flex items-center justify-between rounded-lg border border-ide-border bg-ide-sidebar p-4"
            >
              <div>
                <Link href={`/projects/${project.id}`} className="font-medium text-white hover:underline">
                  {project.name}
                </Link>
                <p className="text-xs text-ide-muted">
                  {project.targetFpga} · {project.toolchain}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(project.id)}
                className="text-sm text-red-400 hover:underline"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
