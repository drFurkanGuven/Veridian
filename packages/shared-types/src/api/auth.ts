export type OAuthProvider = 'google' | 'github';

export type UserRole = 'user' | 'admin';

export type AuditEventType =
  | 'register'
  | 'login_success'
  | 'login_failed'
  | 'oauth_login'
  | 'logout'
  | 'password_changed'
  | 'session_revoked'
  | 'account_locked'
  | 'account_disabled'
  | 'account_enabled'
  | 'role_changed'
  | 'profile_updated';

export interface User {
  id: string;
  email: string;
  displayName: string;
  avatarUrl: string | null;
  emailVerified: boolean;
  role: UserRole;
  isActive: boolean;
  lastLoginAt: string | null;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  displayName: string;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface OAuthProvidersResponse {
  google: boolean;
  github: boolean;
  googleRedirectUri?: string | null;
  githubRedirectUri?: string | null;
}

export interface OAuthUrlResponse {
  url: string;
  state: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
}

export interface LogoutRequest {
  refreshToken: string;
}

export interface UserSession {
  id: string;
  userAgent: string | null;
  ipAddress: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface UpdateProfileRequest {
  displayName: string;
}

export interface AdminUser extends User {
  failedLoginAttempts: number;
  lockedUntil: string | null;
}

export interface UpdateAdminUserRequest {
  isActive?: boolean;
  role?: UserRole;
}

export interface AuditLogEntry {
  id: number;
  userId: string | null;
  targetUserId: string | null;
  eventType: AuditEventType;
  ipAddress: string | null;
  userAgent: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
}

export interface ApiError {
  detail: string;
  code?: string;
  statusCode: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
