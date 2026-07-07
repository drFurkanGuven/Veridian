'use client';

import type {
  ArtifactMeta,
  EditorSelection,
  FileContent,
  FileNode,
  FolderNode,
  JobLogEntry,
  JobStatus,
  ProjectTree,
  Simulator,
} from '@veridian/shared-types';
import { isVcdArtifact } from '@veridian/shared-types';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { AiChatPanel } from '@/components/ai-chat-panel';
import { CodeEditor } from '@/components/code-editor';
import { FileTreeSidebar } from '@/components/file-tree-sidebar';
import { WaveformViewer } from '@/components/waveform-viewer';

import {
  createFile,
  deleteFile,
  getFileContent,
  getProjectTree,
  renameFile,
  updateFileContent,
  upsertFileByPath,
} from '@/lib/files-api';
import {
  connectJobWebSocket,
  downloadArtifact,
  fetchArtifactContent,
  getJobArtifacts,
  startCompilation,
  startSimulation,
} from '@/lib/jobs-api';
import { isLoggedIn } from '@/lib/projects-api';

type RightPanel = 'compile' | 'simulate' | 'ai';
type CenterTab = 'editor' | 'waveform';

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

function suggestNewFileName(existingFiles: FileNode[]): string {
  const usedPaths = new Set(existingFiles.map((file) => file.path));
  let candidate = 'new.v';
  let counter = 2;
  while (usedPaths.has(`/${candidate}`)) {
    candidate = `new-${counter}.v`;
    counter += 1;
  }
  return candidate;
}

function fileBaseName(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

function statusColor(status: JobStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400';
    case 'failed':
      return 'text-red-400';
    case 'running':
      return 'text-blue-400';
    case 'waiting':
      return 'text-yellow-400';
    default:
      return 'text-ide-muted';
  }
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);

  const [tree, setTree] = useState<ProjectTree | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [editorValue, setEditorValue] = useState('');
  const [editorSelection, setEditorSelection] = useState<EditorSelection | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState('');

  const [rightPanel, setRightPanel] = useState<RightPanel>('compile');
  const [topModule, setTopModule] = useState('top');
  const [testbenchFileId, setTestbenchFileId] = useState('');
  const [simulator, setSimulator] = useState<Simulator>('icarus');
  const [jobRunning, setJobRunning] = useState(false);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobLogs, setJobLogs] = useState<JobLogEntry[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactMeta[]>([]);
  const [centerTab, setCenterTab] = useState<CenterTab>('editor');
  const [waveformSource, setWaveformSource] = useState<string | null>(null);
  const [waveformLoading, setWaveformLoading] = useState(false);

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

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const files = tree ? collectFiles(tree) : [];

  const aiBuildContext = useMemo(() => {
    const hasErrorLogs = jobLogs.some((log) => log.level === 'error');
    const includeLogs = jobStatus === 'failed' || hasErrorLogs;
    return {
      ...(jobStatus ? { jobStatus } : {}),
      ...(includeLogs && jobLogs.length > 0
        ? {
            simulationLogs: jobLogs.map((log) => ({
              level: log.level,
              message: log.message,
            })),
          }
        : {}),
      ...(files.length > 0
        ? {
            projectFiles: files.map((file) => ({
              path: file.path,
              language: file.language,
            })),
          }
        : {}),
    };
  }, [files, jobLogs, jobStatus]);

  useEffect(() => {
    if (!testbenchFileId && files.length > 0) {
      const tb = files.find((f) => f.path.includes('tb')) ?? files[0];
      setTestbenchFileId(tb.id);
    }
  }, [files, testbenchFileId]);

  async function openFile(fileId: string) {
    setError('');
    setEditingName(false);
    try {
      const content = await getFileContent(projectId, fileId);
      setSelectedFile(content);
      setEditorValue(content.content);
      setEditorSelection(null);
      setNameDraft(fileBaseName(content.path));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open file');
    }
  }

  async function handleCreateFile() {
    setError('');
    try {
      const freshTree = await getProjectTree(projectId);
      const currentFiles = collectFiles(freshTree);
      let name = suggestNewFileName(currentFiles);

      for (let attempt = 0; attempt < 5; attempt += 1) {
        try {
          const created = await createFile(projectId, {
            name,
            content: 'module top;\nendmodule\n',
          });
          await loadTree();
          await openFile(created.id);
          return;
        } catch (err) {
          const message = err instanceof Error ? err.message.toLowerCase() : '';
          if (!message.includes('already exists') || attempt === 4) {
            throw err;
          }
          name = suggestNewFileName([
            ...currentFiles,
            { path: `/${name}` } as FileNode,
          ]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create file');
    }
  }

  async function handleAiWriteFile(path: string, content: string) {
    setError('');
    try {
      const updated = await upsertFileByPath(projectId, path, content);
      await loadTree();
      setSelectedFile(updated);
      setEditorValue(updated.content);
      setNameDraft(fileBaseName(updated.path));
      setEditorSelection(null);
      setCenterTab('editor');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to write file');
      throw err;
    }
  }

  async function handleSidebarRename(fileId: string, newName: string) {
    setError('');
    try {
      const node = await renameFile(projectId, fileId, newName);
      await loadTree();
      if (selectedFile?.id === fileId) {
        setSelectedFile({
          ...selectedFile,
          path: node.path,
          language: node.language,
        });
        setNameDraft(fileBaseName(node.path));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename file');
      throw err;
    }
  }

  async function handleDeleteFile(fileId: string) {
    setError('');
    try {
      await deleteFile(projectId, fileId);
      await loadTree();
      if (selectedFile?.id === fileId) {
        setSelectedFile(null);
        setEditorValue('');
        setEditorSelection(null);
        setEditingName(false);
        setCenterTab('editor');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete file');
      throw err;
    }
  }

  async function handleSave(contentOverride?: string) {
    if (!selectedFile) return;
    const content = contentOverride ?? editorValue;
    setSaving(true);
    setError('');
    try {
      try {
        const updated = await updateFileContent(projectId, selectedFile.id, {
          content,
          checksum: selectedFile.checksum,
        });
        setSelectedFile(updated);
        setEditorValue(content);
      } catch (firstError) {
        const message = firstError instanceof Error ? firstError.message : '';
        if (!message.toLowerCase().includes('modified')) {
          throw firstError;
        }
        const fresh = await getFileContent(projectId, selectedFile.id);
        const updated = await updateFileContent(projectId, selectedFile.id, {
          content,
          checksum: fresh.checksum,
        });
        setSelectedFile(updated);
        setEditorValue(content);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save file');
    } finally {
      setSaving(false);
    }
  }

  async function commitRename() {
    if (!selectedFile) return;
    const trimmed = nameDraft.trim();
    setEditingName(false);
    if (!trimmed || trimmed === fileBaseName(selectedFile.path)) return;

    setError('');
    try {
      const node = await renameFile(projectId, selectedFile.id, trimmed);
      await loadTree();
      setSelectedFile({
        ...selectedFile,
        path: node.path,
        language: node.language,
      });
      setNameDraft(fileBaseName(node.path));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename file');
      setNameDraft(fileBaseName(selectedFile.path));
    }
  }

  function handleApplyToEditor(content: string) {
    setEditorValue(content);
    setCenterTab('editor');
  }

  async function handleApplyAndSave(content: string) {
    handleApplyToEditor(content);
    await handleSave(content);
  }

  async function openWaveform(artifact: ArtifactMeta) {
    setWaveformLoading(true);
    setError('');
    try {
      const content = await fetchArtifactContent(artifact.downloadUrl);
      setWaveformSource(content);
      setCenterTab('waveform');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load waveform');
    } finally {
      setWaveformLoading(false);
    }
  }

  async function startJob(jobId: string) {
    setWaveformSource(null);
    setCenterTab('editor');
    setJobLogs([]);
    setArtifacts([]);
    setJobStatus('waiting');
    setJobProgress(0);
    wsRef.current?.close();

    const appendLog = (entry: JobLogEntry) => {
      setJobLogs((prev) => {
        if (prev.some((item) => item.sequence === entry.sequence)) return prev;
        return [...prev, entry];
      });
    };

    const ws = connectJobWebSocket(jobId, {
      onLog: appendLog,
      onProgress: setJobProgress,
      onStatus: (status) => {
        setJobStatus(status);
        if (status === 'success' || status === 'failed' || status === 'cancelled') {
          setJobRunning(false);
          getJobArtifacts(jobId)
            .then(setArtifacts)
            .catch(() => undefined);
        }
      },
      onArtifact: (artifact) => {
        setArtifacts((prev) => {
          if (prev.some((item) => item.id === artifact.id)) return prev;
          return [...prev, artifact];
        });
        if (isVcdArtifact(artifact)) {
          openWaveform(artifact).catch(() => undefined);
        }
      },
    });
    wsRef.current = ws;
  }

  async function handleCompile() {
    setRightPanel('compile');
    setError('');
    setJobRunning(true);
    try {
      const result = await startCompilation(projectId, { topModule });
      setJobStatus(result.status);
      await startJob(result.jobId);
    } catch (err) {
      setJobRunning(false);
      setJobStatus('failed');
      setError(err instanceof Error ? err.message : 'Compilation failed to start');
    }
  }

  async function handleSimulate() {
    if (!testbenchFileId) {
      setError('Select a testbench file');
      return;
    }
    setRightPanel('simulate');
    setError('');
    setJobRunning(true);
    try {
      const result = await startSimulation(projectId, {
        simulator,
        testbenchFileId,
        topModule,
      });
      setJobStatus(result.status);
      await startJob(result.jobId);
    } catch (err) {
      setJobRunning(false);
      setJobStatus('failed');
      setError(err instanceof Error ? err.message : 'Simulation failed to start');
    }
  }

  const runLabel =
    rightPanel === 'simulate'
      ? jobRunning
        ? 'Simulating…'
        : 'Simulate'
      : jobRunning
        ? 'Compiling…'
        : 'Compile';

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-ide-border px-6 py-4">
        <div>
          <h1 className="text-xl font-bold text-white">Project IDE</h1>
          <p className="font-mono text-xs text-ide-muted">{projectId}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-ide-muted">
            Top module
            <input
              value={topModule}
              onChange={(e) => setTopModule(e.target.value)}
              className="rounded border border-ide-border bg-ide-bg px-2 py-1 font-mono text-sm text-white"
            />
          </label>
          {rightPanel === 'simulate' && (
            <>
              <label className="flex items-center gap-2 text-sm text-ide-muted">
                Testbench
                <select
                  value={testbenchFileId}
                  onChange={(e) => setTestbenchFileId(e.target.value)}
                  className="rounded border border-ide-border bg-ide-bg px-2 py-1 font-mono text-sm text-white"
                >
                  {files.map((file) => (
                    <option key={file.id} value={file.id}>
                      {file.path}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-ide-muted">
                Simulator
                <select
                  value={simulator}
                  onChange={(e) => setSimulator(e.target.value as Simulator)}
                  className="rounded border border-ide-border bg-ide-bg px-2 py-1 text-sm text-white"
                >
                  <option value="icarus">Icarus</option>
                  <option value="verilator">Verilator</option>
                  <option value="ghdl">GHDL</option>
                </select>
              </label>
            </>
          )}
          {rightPanel !== 'ai' && (
            <button
              type="button"
              onClick={rightPanel === 'simulate' ? handleSimulate : handleCompile}
              disabled={jobRunning}
              className="rounded bg-emerald-600 px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
            >
              {runLabel}
            </button>
          )}
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
              onClick={() => handleSave()}
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

      {error && <p className="shrink-0 px-6 py-2 text-sm text-red-400">{error}</p>}

      <div className="grid min-h-0 flex-1 grid-cols-[240px_1fr_360px] overflow-hidden">
        <FileTreeSidebar
          files={files}
          selectedFileId={selectedFile?.id}
          onOpenFile={(fileId) => {
            openFile(fileId).catch(() => undefined);
          }}
          onRenameFile={handleSidebarRename}
          onDeleteFile={handleDeleteFile}
          onCreateFile={() => {
            handleCreateFile().catch(() => undefined);
          }}
        />

        <section className="flex min-h-0 flex-col overflow-hidden border-r border-ide-border p-4">
          <div className="mb-3 flex gap-2">
            <button
              type="button"
              onClick={() => setCenterTab('editor')}
              className={`rounded px-2 py-1 text-xs ${
                centerTab === 'editor' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              Editor
            </button>
            <button
              type="button"
              onClick={() => setCenterTab('waveform')}
              disabled={!waveformSource && !waveformLoading}
              className={`rounded px-2 py-1 text-xs ${
                centerTab === 'waveform' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              } disabled:opacity-50`}
            >
              Waveform
            </button>
            {waveformLoading && <span className="text-xs text-ide-muted">Loading VCD…</span>}
          </div>

          {centerTab === 'editor' ? (
            selectedFile ? (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div className="mb-2 flex shrink-0 items-center gap-2">
                  {editingName ? (
                    <input
                      autoFocus
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onBlur={() => {
                        commitRename().catch(() => undefined);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          commitRename().catch(() => undefined);
                        }
                        if (e.key === 'Escape') {
                          setEditingName(false);
                          setNameDraft(fileBaseName(selectedFile.path));
                        }
                      }}
                      className="rounded border border-ide-accent bg-ide-bg px-2 py-0.5 font-mono text-sm text-white"
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        setNameDraft(fileBaseName(selectedFile.path));
                        setEditingName(true);
                      }}
                      className="font-mono text-sm text-white underline decoration-dotted hover:text-emerald-400"
                      title="Click to rename"
                    >
                      {selectedFile.path}
                    </button>
                  )}
                  <span className="ml-auto text-xs uppercase text-ide-muted">{selectedFile.language}</span>
                </div>
                <CodeEditor
                  value={editorValue}
                  language={selectedFile.language}
                  path={selectedFile.path}
                  onChange={setEditorValue}
                  onSelectionChange={setEditorSelection}
                  onSave={() => handleSave()}
                  className="min-h-0 flex-1 rounded border border-ide-border"
                />
              </div>
            ) : (
              <p className="text-ide-muted">Select a file or create a new one.</p>
            )
          ) : waveformSource ? (
            <WaveformViewer source={waveformSource} className="min-h-0 flex-1" />
          ) : (
            <p className="text-ide-muted">Run a simulation with VCD output to view waveforms.</p>
          )}
        </section>

        <aside className="flex min-h-0 flex-col overflow-hidden p-4">
          <div className="mb-3 flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => setRightPanel('compile')}
              className={`rounded px-2 py-1 text-xs ${
                rightPanel === 'compile' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              Compile
            </button>
            <button
              type="button"
              onClick={() => setRightPanel('simulate')}
              className={`rounded px-2 py-1 text-xs ${
                rightPanel === 'simulate' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              Simulate
            </button>
            <button
              type="button"
              onClick={() => setRightPanel('ai')}
              className={`rounded px-2 py-1 text-xs ${
                rightPanel === 'ai' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              AI
            </button>
            {rightPanel !== 'ai' && jobStatus && (
              <span className={`ml-auto text-xs font-medium ${statusColor(jobStatus)}`}>
                {jobStatus} {jobProgress > 0 ? `(${jobProgress}%)` : ''}
              </span>
            )}
          </div>

          <div className={rightPanel === 'ai' ? 'flex min-h-0 flex-1 flex-col' : 'hidden'}>
            <AiChatPanel
              projectId={projectId}
              activeFileId={selectedFile?.id}
              activeFilePath={selectedFile?.path}
              editorContent={editorValue}
              editorSelection={editorSelection}
              buildContext={aiBuildContext}
              onApplyToEditor={handleApplyToEditor}
              onWriteFile={handleAiWriteFile}
              onApplyAndSave={(content) => {
                handleApplyAndSave(content).catch((err: unknown) => {
                  setError(err instanceof Error ? err.message : 'Failed to save');
                });
              }}
              className="min-h-0 flex-1"
            />
          </div>

          <div className={rightPanel === 'ai' ? 'hidden' : 'flex min-h-0 flex-1 flex-col'}>
            <div className="mb-4 h-1 shrink-0 overflow-hidden rounded bg-ide-sidebar">
              <div
                className="h-full bg-emerald-500 transition-all"
                style={{ width: `${jobProgress}%` }}
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto rounded border border-ide-border bg-ide-bg p-3 font-mono text-xs text-ide-muted">
                {rightPanel === 'simulate' && jobLogs.length === 0 && (
                  <p className="mb-2 text-yellow-400/90">
                    Testbench must call $dumpfile(&quot;dump.vcd&quot;) for waveform capture.
                  </p>
                )}
                {jobLogs.length === 0 ? (
                  <p>{rightPanel === 'compile' ? 'Compile' : 'Simulation'} logs appear here.</p>
                ) : (
                  jobLogs.map((log) => (
                    <p
                      key={log.sequence}
                      className={
                        log.level === 'error'
                          ? 'text-red-400'
                          : log.level === 'warn'
                            ? 'text-yellow-400'
                            : ''
                      }
                    >
                      {log.message}
                    </p>
                  ))
                )}
            </div>
            {artifacts.length > 0 && (
              <div className="mt-4 shrink-0">
                <h3 className="mb-2 text-xs font-semibold uppercase text-ide-muted">Artifacts</h3>
                <ul className="space-y-1 text-sm">
                  {artifacts.map((artifact) => (
                    <li key={artifact.id} className="flex flex-wrap items-center gap-2">
                      <span className="text-ide-text">{artifact.name}</span>
                      {isVcdArtifact(artifact) && (
                        <button
                          type="button"
                          onClick={() => {
                            openWaveform(artifact).catch((err: unknown) => {
                              setError(
                                err instanceof Error ? err.message : 'Failed to open waveform',
                              );
                            });
                          }}
                          className="text-sky-400 underline"
                        >
                          View
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          downloadArtifact(artifact.downloadUrl, artifact.name).catch(
                            (err: unknown) => {
                              setError(err instanceof Error ? err.message : 'Download failed');
                            },
                          );
                        }}
                        className="text-emerald-400 underline"
                      >
                        Download
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
