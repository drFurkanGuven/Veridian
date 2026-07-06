import type { JobStatus } from '@veridian/shared-types';
import Link from 'next/link';

const API_PUBLIC_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_SERVER_URL = process.env.API_INTERNAL_URL ?? API_PUBLIC_URL;

async function checkApiHealth(): Promise<{ status: string; version: string } | null> {
  try {
    const response = await fetch(`${API_SERVER_URL}/health`, {
      next: { revalidate: 0 },
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const health = await checkApiHealth();

  const jobStatuses: JobStatus[] = ['waiting', 'running', 'success', 'failed', 'cancelled'];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl space-y-8">
        <header className="space-y-2 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white">Veridian</h1>
          <p className="text-ide-muted">
            The cloud IDE for HDL — Verilog, SystemVerilog, VHDL, synthesis, and simulation.
          </p>
          <div className="flex justify-center gap-4 pt-2 text-sm">
            <Link href="/login" className="text-white underline">
              Sign in
            </Link>
            <Link href="/register" className="text-ide-muted underline hover:text-white">
              Register
            </Link>
            <Link href="/projects" className="text-ide-muted underline hover:text-white">
              Projects
            </Link>
          </div>
        </header>

        <section className="rounded-lg border border-ide-border bg-ide-sidebar p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ide-muted">
            System Status
          </h2>
          <dl className="space-y-3">
            <div className="flex items-center justify-between">
              <dt className="text-sm">Frontend</dt>
              <dd className="flex items-center gap-2 text-sm text-green-400">
                <span className="h-2 w-2 rounded-full bg-green-400" />
                Running
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-sm">API ({API_PUBLIC_URL})</dt>
              <dd className="flex items-center gap-2 text-sm">
                {health ? (
                  <span className="flex items-center gap-2 text-green-400">
                    <span className="h-2 w-2 rounded-full bg-green-400" />
                    {health.status} v{health.version}
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-yellow-400">
                    <span className="h-2 w-2 rounded-full bg-yellow-400" />
                    Offline — start with <code className="font-mono text-xs">pnpm dev</code>
                  </span>
                )}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-sm">Shared Types</dt>
              <dd className="font-mono text-xs text-ide-muted">
                JobStatus: {jobStatuses.join(' | ')}
              </dd>
            </div>
          </dl>
        </section>

        <footer className="text-center text-xs text-ide-muted">
          Phase 9 — Simulation jobs live. Waveform viewer next.
        </footer>
      </div>
    </main>
  );
}
