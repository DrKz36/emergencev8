/**
 * @module features/threads/threads-service
 * Service utilitaire pour orchestrer les appels HTTP de la persistance des threads.
 */
import { api } from '../../shared/api-client.js';

const HEX32 = /^[0-9a-f]{32}$/i;
const UUID36 = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function sanitizeThreadId(value) {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (HEX32.test(trimmed) || UUID36.test(trimmed)) return trimmed;
  }
  if (value != null) {
    const str = String(value).trim();
    if (HEX32.test(str) || UUID36.test(str)) return str;
  }
  return null;
}

function wrapError(error, fallbackMessage) {
  if (error instanceof Error) {
    if (fallbackMessage && !error.message) error.message = fallbackMessage;
    return error;
  }
  const wrapped = new Error(fallbackMessage || 'Thread service error');
  if (error && typeof error === 'object' && 'status' in error) {
    wrapped.status = error.status;
  }
  return wrapped;
}

function normalizeRecord(raw, fallbackId = null) {
  if (!raw || typeof raw !== 'object') {
    return fallbackId ? { id: fallbackId } : null;
  }
  const normalized = { ...raw };
  const candidateId = sanitizeThreadId(normalized.id ?? fallbackId);
  normalized.id = candidateId;
  normalized.archived = normalized.archived === true || normalized.archived === 1;
  if (normalized.meta && typeof normalized.meta === 'string') {
    try {
      normalized.meta = JSON.parse(normalized.meta);
    } catch {
      normalized.meta = normalized.meta;
    }
  }
  if (typeof normalized.title === 'string') {
    normalized.title = normalized.title.trim();
  }
  if (typeof normalized.agent_id !== 'string' && typeof normalized.agentId === 'string') {
    normalized.agent_id = normalized.agentId;
  }
  if (normalized.agent_id && typeof normalized.agent_id === 'string') {
    normalized.agent_id = normalized.agent_id.trim();
  }
  return normalized.id ? normalized : null;
}

export async function fetchThreads(params = {}) {
  try {
    const response = await api.listThreads(params);
    const items = Array.isArray(response?.items) ? response.items : [];
    return items
      .map((item) => normalizeRecord(item))
      .filter(Boolean);
  } catch (error) {
    throw wrapError(error, 'Impossible de recuperer les threads.');
  }
}

export async function fetchThreadDetail(id, options = {}) {
  const safeId = sanitizeThreadId(id);
  if (!safeId) {
    const err = new Error('Identifiant de thread invalide');
    err.status = 400;
    throw err;
  }
  try {
    return await api.getThreadById(safeId, options);
  } catch (error) {
    throw wrapError(error, 'Impossible de charger le thread demande.');
  }
}

export async function createThread({ type = 'chat', title, agentId, agent_id, metadata, meta } = {}) {
  const safeType = String(type) === 'debate' ? 'debate' : 'chat';
  const resolvedTitle = typeof title === 'string' && title.trim() ? title.trim() : undefined;
  const resolvedAgent = (typeof agentId === 'string' && agentId.trim())
    ? agentId.trim()
    : (typeof agent_id === 'string' && agent_id.trim() ? agent_id.trim() : undefined);
  const resolvedMeta = meta ?? metadata;
  try {
    const result = await api.createThread({
      type: safeType,
      title: resolvedTitle,
      agent_id: resolvedAgent,
      metadata: resolvedMeta,
    });
    const normalizedThread = normalizeRecord(result?.thread, result?.id ?? null);
    const id = normalizedThread?.id ?? sanitizeThreadId(result?.id);
    return {
      id,
      thread: normalizedThread ?? (id ? { id } : null),
    };
  } catch (error) {
    throw wrapError(error, 'Impossible de creer un nouveau thread.');
  }
}

export async function updateThread(id, updates = {}) {
  const safeId = sanitizeThreadId(id);
  if (!safeId) {
    const err = new Error('Identifiant de thread invalide');
    err.status = 400;
    throw err;
  }
  try {
    const thread = await api.updateThread(safeId, updates);
    return thread ? normalizeRecord(thread, safeId) : null;
  } catch (error) {
    throw wrapError(error, 'Impossible de mettre a jour le thread.');
  }
}

export async function archiveThread(id) {
  const updated = await updateThread(id, { archived: true });
  return updated;
}
