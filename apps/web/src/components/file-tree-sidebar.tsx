'use client';

import type { FileNode } from '@veridian/shared-types';
import { useState } from 'react';

interface FileTreeSidebarProps {
  files: FileNode[];
  selectedFileId?: string | null;
  onOpenFile: (fileId: string) => void;
  onRenameFile: (fileId: string, newName: string) => Promise<void>;
  onDeleteFile: (fileId: string) => Promise<void>;
  onCreateFile: () => void;
}

function fileBaseName(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

export function FileTreeSidebar({
  files,
  selectedFileId,
  onOpenFile,
  onRenameFile,
  onDeleteFile,
  onCreateFile,
}: FileTreeSidebarProps) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  async function commitRename(file: FileNode) {
    const trimmed = nameDraft.trim();
    setRenamingId(null);
    if (!trimmed || trimmed === fileBaseName(file.path)) return;

    setBusyId(file.id);
    try {
      await onRenameFile(file.id, trimmed);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(file: FileNode) {
    const confirmed = window.confirm(`Delete ${file.path}? This cannot be undone.`);
    if (!confirmed) return;

    setBusyId(file.id);
    try {
      await onDeleteFile(file.id);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden border-r border-ide-border p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase text-ide-muted">Files</h2>
        <button
          type="button"
          onClick={onCreateFile}
          className="rounded border border-ide-border px-2 py-0.5 text-[10px] text-ide-muted hover:bg-ide-sidebar"
          title="New file"
        >
          + New
        </button>
      </div>

      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto text-sm">
        {files.map((file) => {
          const isSelected = selectedFileId === file.id;
          const isRenaming = renamingId === file.id;
          const isBusy = busyId === file.id;

          return (
            <li
              key={file.id}
              className={`group rounded ${isSelected ? 'bg-ide-sidebar' : 'hover:bg-ide-sidebar/60'}`}
            >
              <div className="flex items-center gap-1 px-1 py-1">
                {isRenaming ? (
                  <input
                    autoFocus
                    value={nameDraft}
                    onChange={(event) => setNameDraft(event.target.value)}
                    onBlur={() => {
                      commitRename(file).catch(() => undefined);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        commitRename(file).catch(() => undefined);
                      }
                      if (event.key === 'Escape') {
                        setRenamingId(null);
                      }
                    }}
                    className="min-w-0 flex-1 rounded border border-ide-accent bg-ide-bg px-2 py-0.5 font-mono text-xs text-white"
                  />
                ) : (
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => onOpenFile(file.id)}
                    className={`min-w-0 flex-1 truncate px-1 py-0.5 text-left font-mono text-xs ${
                      isSelected ? 'text-white' : 'text-ide-muted'
                    }`}
                    title={file.path}
                  >
                    {file.path}
                  </button>
                )}

                {!isRenaming && (
                  <div className="flex shrink-0 gap-0.5 opacity-0 transition group-hover:opacity-100">
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        setRenamingId(file.id);
                        setNameDraft(fileBaseName(file.path));
                      }}
                      className="rounded px-1 text-[10px] text-ide-muted hover:bg-ide-bg hover:text-white"
                      title="Rename"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        handleDelete(file).catch(() => undefined);
                      }}
                      className="rounded px-1 text-[10px] text-red-400 hover:bg-ide-bg"
                      title="Delete"
                    >
                      ×
                    </button>
                  </div>
                )}
              </div>
            </li>
          );
        })}
        {files.length === 0 && <li className="text-xs text-ide-muted">No files yet</li>}
      </ul>
    </aside>
  );
}
