'use client';

import type { FileContent, FileNode, FolderNode, ProjectTree } from '@veridian/shared-types';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import {
  createFile,
  getFileContent,
  getProjectTree,
  updateFileContent,
} from '@/lib/files-api';
import { isLoggedIn } from '@/lib/projects-api';

function collectFiles(tree: ProjectTree): FileNode[] {
  const files = [...tree.rootFiles];
  const walk = (folders: FolderNode[]) => {
    for (const folder of folders) {
      files.push(...folder.files);
      walk(folder.children);
    }
  };
  walk(tree.rootFolders);
  return files;
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();

  const [tree, setTree] = useState<ProjectTree | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [editorValue, setEditorValue] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const loadTree = useCallback(async () => {
    const data = await getProjectTree(projectId);
    setTree(data);
  }, [projectId]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login');
      return;
    }
    loadTree().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    });
  }, [loadTree, router]);

  async function openFile(fileId: string) {
    setError('');
    try {
      const content = await getFileContent(projectId, fileId);
      setSelectedFile(content);
      setEditorValue(content.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open file');
    }
  }

  async function handleCreateFile() {
    setError('');
    try {
      const created = await createFile(projectId, {
        name: 'top.v',
        content: 'module top;\nendmodule\n',
      });
      await loadTree();
      await openFile(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create file');
    }
  }

  async function handleSave() {
    if (!selectedFile) return;
    setSaving(true);
    setError('');
    try {
      const updated = await updateFileContent(projectId, selectedFile.id, {
        content: editorValue,
        checksum: selectedFile.checksum,
      });
      setSelectedFile(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save file');
    } finally {
      setSaving(false);
    }
  }

  const files = tree ? collectFiles(tree) : [];

  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-ide-border px-6 py-4">
        <div>
          <h1 className="text-xl font-bold text-white">Project IDE</h1>
          <p className="font-mono text-xs text-ide-muted">{projectId}</p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleCreateFile}
            className="rounded border border-ide-border px-3 py-1 text-sm hover:bg-ide-sidebar"
          >
            New file
          </button>
          {selectedFile && (
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded bg-white px-3 py-1 text-sm font-medium text-black disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          )}
          <Link href="/projects" className="text-sm text-ide-muted underline">
            Back
          </Link>
        </div>
      </header>

      {error && <p className="px-6 py-2 text-sm text-red-400">{error}</p>}

      <div className="grid flex-1 grid-cols-[240px_1fr]">
        <aside className="border-r border-ide-border p-4">
          <h2 className="mb-3 text-xs font-semibold uppercase text-ide-muted">Files</h2>
          <ul className="space-y-1 text-sm">
            {files.map((file) => (
              <li key={file.id}>
                <button
                  type="button"
                  onClick={() => openFile(file.id)}
                  className={`w-full rounded px-2 py-1 text-left hover:bg-ide-sidebar ${
                    selectedFile?.id === file.id ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
                  }`}
                >
                  {file.path}
                </button>
              </li>
            ))}
            {files.length === 0 && <li className="text-ide-muted">No files yet</li>}
          </ul>
        </aside>

        <section className="p-4">
          {selectedFile ? (
            <div className="h-full">
              <p className="mb-2 font-mono text-xs text-ide-muted">{selectedFile.path}</p>
              <textarea
                value={editorValue}
                onChange={(e) => setEditorValue(e.target.value)}
                className="h-[70vh] w-full resize-none rounded border border-ide-border bg-ide-bg p-4 font-mono text-sm text-ide-text"
                spellCheck={false}
              />
            </div>
          ) : (
            <p className="text-ide-muted">Select a file or create a new one.</p>
          )}
        </section>
      </div>
    </main>
  );
}
