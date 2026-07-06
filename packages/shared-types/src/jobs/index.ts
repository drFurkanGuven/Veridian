export type JobStatus = 'waiting' | 'running' | 'success' | 'failed' | 'cancelled';

export type LogLevel = 'info' | 'warn' | 'error';

export type Simulator = 'icarus' | 'verilator' | 'ghdl';

export type ArtifactType = 'bitstream' | 'log' | 'vcd' | 'json_report';

export interface JobLogEntry {
  sequence: number;
  level: LogLevel;
  message: string;
  createdAt: string;
}

export interface ArtifactMeta {
  id: string;
  name: string;
  artifactType: ArtifactType;
  sizeBytes: number;
  mimeType: string;
  downloadUrl: string;
  createdAt: string;
}

export interface CompilationJob {
  id: string;
  projectId: string;
  userId: string;
  status: JobStatus;
  toolchain: string;
  topModule: string;
  constraintFileId: string | null;
  progress: number;
  errorMessage: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
}

export interface SimulationJob {
  id: string;
  projectId: string;
  userId: string;
  status: JobStatus;
  simulator: Simulator;
  testbenchFileId: string;
  topModule: string;
  progress: number;
  errorMessage: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
}

export interface CompileRequest {
  topModule: string;
  constraintFileId?: string;
}

export interface CompileResponse {
  jobId: string;
  status: JobStatus;
  wsUrl: string;
}

export interface SimulateRequest {
  simulator: Simulator;
  testbenchFileId: string;
  topModule: string;
}

export interface SimulateResponse {
  jobId: string;
  status: JobStatus;
  wsUrl: string;
}
