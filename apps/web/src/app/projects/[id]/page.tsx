'use client';

import type {
  ArtifactMeta,
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
import { useCallback, useEffect, useRef, useState } from 'react';

import { WaveformViewer } from '@/components/waveform-viewer';

import {
  createFile,
  getFileContent,
  getProjectTree,
  updateFileContent,
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

type BuildMode = 'compile' | 'simulate';
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
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [buildMode, setBuildMode] = useState<BuildMode>('compile');
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

  useEffect(() => {
    if (!testbenchFileId && files.length > 0) {
      const tb = files.find((f) => f.path.includes('tb')) ?? files[0];
      setTestbenchFileId(tb.id);
    }
  }, [files, testbenchFileId]);

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
    buildMode === 'compile'
      ? jobRunning
        ? 'Compiling…'
        : 'Compile'
      : jobRunning
        ? 'Simulating…'
        : 'Simulate';

  return (
    <main className="flex min-h-screen flex-col">
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
          {buildMode === 'simulate' && (
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
          <button
            type="button"
            onClick={buildMode === 'compile' ? handleCompile : handleSimulate}
            disabled={jobRunning}
            className="rounded bg-emerald-600 px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
          >
            {runLabel}
          </button>
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

      <div className="grid flex-1 grid-cols-[240px_1fr_320px]">
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

        <section className="flex min-h-0 flex-col border-r border-ide-border p-4">
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
            )
          ) : waveformSource ? (
            <WaveformViewer source={waveformSource} className="h-[70vh]" />
          ) : (
            <p className="text-ide-muted">Run a simulation with VCD output to view waveforms.</p>
          )}
        </section>

        <aside className="flex flex-col p-4">
          <div className="mb-3 flex gap-2">
            <button
              type="button"
              onClick={() => setBuildMode('compile')}
              className={`rounded px-2 py-1 text-xs ${
                buildMode === 'compile' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              Compile
            </button>
            <button
              type="button"
              onClick={() => setBuildMode('simulate')}
              className={`rounded px-2 py-1 text-xs ${
                buildMode === 'simulate' ? 'bg-ide-sidebar text-white' : 'text-ide-muted'
              }`}
            >
              Simulate
            </button>
            {jobStatus && (
              <span className={`ml-auto text-xs font-medium ${statusColor(jobStatus)}`}>
                {jobStatus} {jobProgress > 0 ? `(${jobProgress}%)` : ''}
              </span>
            )}
          </div>
          <div className="mb-4 h-1 overflow-hidden rounded bg-ide-sidebar">
            <div
              className="h-full bg-emerald-500 transition-all"
              style={{ width: `${jobProgress}%` }}
            />
          </div>
          <div className="flex-1 overflow-y-auto rounded border border-ide-border bg-ide-bg p-3 font-mono text-xs text-ide-muted">
            {buildMode === 'simulate' && jobLogs.length === 0 && (
              <p className="mb-2 text-yellow-400/90">
                Testbench must call $dumpfile(&quot;dump.vcd&quot;) for waveform capture.
              </p>
            )}
            {jobLogs.length === 0 ? (
              <p>{buildMode === 'compile' ? 'Compile' : 'Simulation'} logs appear here.</p>
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
            <div className="mt-4">
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
                            setError(err instanceof Error ? err.message : 'Failed to open waveform');
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
                        downloadArtifact(artifact.downloadUrl, artifact.name).catch((err: unknown) => {
                          setError(err instanceof Error ? err.message : 'Download failed');
                        });
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
        </aside>
      </div>
    </main>
  );
}
