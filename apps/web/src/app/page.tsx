'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { isLoggedIn } from '@/lib/projects-api';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(isLoggedIn() ? '/projects' : '/login');
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-ide-bg">
      <p className="text-sm text-ide-muted">Loading…</p>
    </main>
  );
}
