'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { OAuthButtons } from '@/components/oauth-buttons';
import { loginUser, saveAuthTokens } from '@/lib/auth-api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await loginUser({ email, password });
      saveAuthTokens(result.tokens);
      router.push('/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-ide-bg">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-40 -top-40 h-[520px] w-[520px] rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-[520px] w-[520px] rounded-full bg-sky-500/10 blur-3xl" />
      </div>

      <div className="relative mx-auto grid min-h-screen w-full max-w-6xl grid-cols-1 gap-10 px-6 py-10 lg:grid-cols-2 lg:items-center lg:px-10">
        <section className="space-y-7">
          <header className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-ide-border bg-ide-sidebar/40 px-3 py-1 text-[11px] text-ide-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Cloud FPGA IDE · Editor · Simulation · Waveforms · AI
            </div>
            <h1 className="text-balance text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Veridian: FPGA development that stays in flow.
            </h1>
            <p className="max-w-xl text-pretty text-sm leading-relaxed text-ide-muted sm:text-base">
              Write HDL, run simulations, inspect waveforms, and iterate with an AI assistant — all in one
              workspace. Built for Verilog, SystemVerilog, and VHDL.
            </p>
          </header>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-ide-border bg-ide-sidebar/50 p-4">
              <p className="text-xs font-semibold text-white">Monaco HDL editor</p>
              <p className="mt-1 text-xs text-ide-muted">Syntax highlight, selection-aware AI, save-safe edits.</p>
            </div>
            <div className="rounded-lg border border-ide-border bg-ide-sidebar/50 p-4">
              <p className="text-xs font-semibold text-white">Simulation &amp; logs</p>
              <p className="mt-1 text-xs text-ide-muted">Compile/sim output is captured and shared with AI context.</p>
            </div>
            <div className="rounded-lg border border-ide-border bg-ide-sidebar/50 p-4">
              <p className="text-xs font-semibold text-white">Waveform viewer</p>
              <p className="mt-1 text-xs text-ide-muted">Open VCDs in-browser and debug timing quickly.</p>
            </div>
            <div className="rounded-lg border border-ide-border bg-ide-sidebar/50 p-4">
              <p className="text-xs font-semibold text-white">Cursor-like AI writes</p>
              <p className="mt-1 text-xs text-ide-muted">AI can create/update project files with tool blocks.</p>
            </div>
          </div>

          <div className="rounded-lg border border-ide-border bg-ide-sidebar/40 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ide-muted">What you get</p>
            <ul className="mt-3 space-y-2 text-sm text-ide-text">
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                Projects + file tree + safe saves
              </li>
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                Compile/simulate pipeline with artifacts
              </li>
              <li className="flex gap-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                AI chat integrated with the editor and logs
              </li>
            </ul>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-ide-muted">
            <span>© {new Date().getFullYear()} Veridian</span>
          </div>
        </section>

        <section className="w-full">
          <div className="mx-auto w-full max-w-md space-y-6 rounded-xl border border-ide-border bg-ide-sidebar p-8 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
            <header className="space-y-2">
              <h2 className="text-xl font-semibold text-white">Sign in</h2>
              <p className="text-sm text-ide-muted">Use email/password, Google, or GitHub.</p>
            </header>

            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="block space-y-1 text-sm">
                <span className="text-ide-muted">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  className="w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-ide-text outline-none ring-emerald-500/30 focus:ring-2"
                />
              </label>
              <label className="block space-y-1 text-sm">
                <span className="text-ide-muted">Password</span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="w-full rounded border border-ide-border bg-ide-bg px-3 py-2 text-ide-text outline-none ring-emerald-500/30 focus:ring-2"
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

            <OAuthButtons onError={setError} />

            <p className="text-center text-sm text-ide-muted">
              No account?{' '}
              <Link href="/register" className="text-white underline">
                Register
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
