export type HdlLanguage = 'verilog' | 'systemverilog' | 'vhdl' | 'xdc' | 'qsf';

export type Toolchain = 'yosys-nextpnr' | 'yosys' | 'icarus' | 'verilator' | 'ghdl';

export type FpgaTarget = 'ice40' | 'ecp5' | 'generic';

export interface Project {
  id: string;
  userId: string;
  name: string;
  description: string | null;
  targetFpga: FpgaTarget;
  toolchain: Toolchain;
  lastOpenedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  targetFpga?: FpgaTarget;
  toolchain?: Toolchain;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  targetFpga?: FpgaTarget;
  toolchain?: Toolchain;
}

export interface FolderNode {
  id: string;
  name: string;
  path: string;
  parentId: string | null;
  children: FolderNode[];
  files: FileNode[];
}

export interface FileNode {
  id: string;
  name: string;
  path: string;
  language: HdlLanguage;
  sizeBytes: number;
  updatedAt: string;
}

export interface ProjectTree {
  projectId: string;
  rootFolders: FolderNode[];
  rootFiles: FileNode[];
}

export interface FileContent {
  id: string;
  path: string;
  content: string;
  language: HdlLanguage;
  checksum: string;
  updatedAt: string;
}

export interface CreateFileRequest {
  name: string;
  folderId?: string;
  content?: string;
  language?: HdlLanguage;
}

export interface UpdateFileContentRequest {
  content: string;
  checksum: string;
}

export interface CreateFolderRequest {
  name: string;
  parentId?: string;
}

export interface RenameRequest {
  name: string;
}

export interface MoveRequest {
  parentId?: string;
}
