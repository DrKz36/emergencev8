/**
 * @module features/threads/threads-service
 * Service utilitaire pour orchestrer les appels HTTP de la persistance des threads.
 */
import { api } from '../../shared/api-client.js';
const HEX32 = /^[0-9a-f]{32}$/i;
const UUID36 = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

let papaPromise;
let jsPdfPromise;

async function loadPapaParse() {
  if (!papaPromise) {
    papaPromise = import('papaparse').then((module) => module.default ?? module);
  }
  return papaPromise;
}

async function loadJsPdf() {
  if (!jsPdfPromise) {
    jsPdfPromise = import('jspdf')
      .then(async (module) => {
        const jsPDF = module.jsPDF ?? module.default ?? module;
        try {
          const scope = typeof globalThis !== 'undefined' ? globalThis : window;
          if (scope) {
            scope.jspdf = scope.jspdf || {};
            if (!scope.jspdf.jsPDF) {
              scope.jspdf.jsPDF = jsPDF;
            }
            if (!scope.jsPDF) {
              scope.jsPDF = jsPDF;
            }
          }
        } catch {
          // ignore if global scope is not writable
        }
        await import('jspdf-autotable');
        return jsPDF;
      });
  }
  return jsPdfPromise;
}

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

export async function fetchArchivedThreads(params = {}) {
  try {
    const response = await api.get('/api/threads/archived/list', params);
    const items = Array.isArray(response?.items) ? response.items : [];
    return items
      .map((item) => normalizeRecord(item))
      .filter(Boolean);
  } catch (error) {
    throw wrapError(error, 'Impossible de recuperer les threads archives.');
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

export async function unarchiveThread(id) {
  const updated = await updateThread(id, { archived: false });
  return updated;
}

export async function deleteThread(id) {
  const safeId = sanitizeThreadId(id);
  if (!safeId) {
    const err = new Error('Identifiant de thread invalide');
    err.status = 400;
    throw err;
  }
  try {
    await api.deleteThread(safeId);
    return true;
  } catch (error) {
    throw wrapError(error, 'Impossible de supprimer le thread.');
  }
}

/**
 * Export functions for threads
 */

function formatDate(dateString) {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return date.toLocaleString('fr-FR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
}

function downloadFile(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function exportThreadToJSON(threadId) {
  const safeId = sanitizeThreadId(threadId);
  if (!safeId) {
    throw new Error('Identifiant de thread invalide');
  }

  try {
    const threadData = await fetchThreadDetail(safeId, { include_messages: true });

    const exportData = {
      metadata: {
        exported_at: new Date().toISOString(),
        thread_id: threadData.id,
        thread_title: threadData.title || 'Sans titre',
        agent_id: threadData.agent_id || null,
        created_at: threadData.created_at,
        updated_at: threadData.updated_at,
        message_count: threadData.messages?.length || 0
      },
      thread: {
        id: threadData.id,
        title: threadData.title,
        agent_id: threadData.agent_id,
        type: threadData.type,
        created_at: threadData.created_at,
        updated_at: threadData.updated_at,
        archived: threadData.archived,
        meta: threadData.meta
      },
      messages: (threadData.messages || []).map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        created_at: msg.created_at,
        tokens: msg.tokens,
        model: msg.model,
        cost: msg.cost
      }))
    };

    const jsonString = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `conversation-${safeId.slice(0, 8)}-${timestamp}.json`;

    downloadFile(blob, filename);
    return { success: true, filename };
  } catch (error) {
    throw wrapError(error, 'Impossible d\'exporter le thread en JSON');
  }
}

export async function exportThreadToCSV(threadId) {
  const safeId = sanitizeThreadId(threadId);
  if (!safeId) {
    throw new Error('Identifiant de thread invalide');
  }

  try {
    const threadData = await fetchThreadDetail(safeId, { include_messages: true });

    const messages = threadData.messages || [];

    // Préparer les données pour CSV
    const csvData = messages.map(msg => ({
      'ID Message': msg.id || '',
      'Date': formatDate(msg.created_at),
      'Role': msg.role || '',
      'Contenu': (msg.content || '').replace(/\n/g, ' ').replace(/"/g, '""'),
      'Tokens': msg.tokens || 0,
      'Modele': msg.model || '',
      'Cout ($)': msg.cost || 0
    }));

    // Ajouter métadonnées en en-tête
    const headerData = [
      { 'ID Message': 'METADONNEES', 'Date': '', 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'Thread ID', 'Date': threadData.id, 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'Titre', 'Date': threadData.title || 'Sans titre', 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'Agent', 'Date': threadData.agent_id || 'N/A', 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'Cree le', 'Date': formatDate(threadData.created_at), 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'Nombre de messages', 'Date': String(messages.length), 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': '', 'Date': '', 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' },
      { 'ID Message': 'MESSAGES', 'Date': '', 'Role': '', 'Contenu': '', 'Tokens': '', 'Modele': '', 'Cout ($)': '' }
    ];

    const allData = [...headerData, ...csvData];
    const Papa = await loadPapaParse();
    const csv = Papa.unparse(allData, {
      quotes: true,
      delimiter: ',',
      header: true
    });

    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `conversation-${safeId.slice(0, 8)}-${timestamp}.csv`;

    downloadFile(blob, filename);
    return { success: true, filename };
  } catch (error) {
    throw wrapError(error, 'Impossible d\'exporter le thread en CSV');
  }
}

export async function exportThreadToPDF(threadId) {
  const safeId = sanitizeThreadId(threadId);
  if (!safeId) {
    throw new Error('Identifiant de thread invalide');
  }

  try {
    const threadData = await fetchThreadDetail(safeId, { include_messages: true });

    const jsPDF = await loadJsPdf();
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 15;
    const maxWidth = pageWidth - 2 * margin;

    // En-tête
    doc.setFontSize(18);
    doc.setFont(undefined, 'bold');
    doc.text('Conversation Emergence', margin, 20);

    // Métadonnées
    doc.setFontSize(10);
    doc.setFont(undefined, 'normal');
    let yPos = 35;

    const metadata = [
      ['Titre', threadData.title || 'Sans titre'],
      ['Thread ID', threadData.id],
      ['Agent', threadData.agent_id || 'N/A'],
      ['Date de creation', formatDate(threadData.created_at)],
      ['Derniere mise a jour', formatDate(threadData.updated_at)],
      ['Nombre de messages', String(threadData.messages?.length || 0)]
    ];

    doc.autoTable({
      startY: yPos,
      head: [['Propriete', 'Valeur']],
      body: metadata,
      theme: 'grid',
      headStyles: { fillColor: [56, 189, 248], textColor: 255 },
      margin: { left: margin, right: margin },
      styles: { fontSize: 9 }
    });

    yPos = doc.lastAutoTable.finalY + 10;

    // Messages
    const messages = threadData.messages || [];

    if (messages.length > 0) {
      doc.setFontSize(14);
      doc.setFont(undefined, 'bold');

      if (yPos > pageHeight - 30) {
        doc.addPage();
        yPos = 20;
      }

      doc.text('Messages', margin, yPos);
      yPos += 8;

      messages.forEach((msg, index) => {
        if (yPos > pageHeight - 40) {
          doc.addPage();
          yPos = 20;
        }

        // Role badge
        doc.setFontSize(10);
        doc.setFont(undefined, 'bold');
        const roleColor = msg.role === 'user' ? [99, 102, 241] : [139, 92, 246];
        doc.setTextColor(...roleColor);
        doc.text(`${msg.role.toUpperCase()}`, margin, yPos);

        // Date
        doc.setTextColor(100, 100, 100);
        doc.setFont(undefined, 'normal');
        doc.setFontSize(8);
        doc.text(formatDate(msg.created_at), margin + 25, yPos);

        yPos += 5;

        // Content
        doc.setTextColor(0, 0, 0);
        doc.setFontSize(9);
        doc.setFont(undefined, 'normal');

        const content = (msg.content || 'Contenu vide').substring(0, 500);
        const lines = doc.splitTextToSize(content, maxWidth);

        lines.forEach(line => {
          if (yPos > pageHeight - 20) {
            doc.addPage();
            yPos = 20;
          }
          doc.text(line, margin, yPos);
          yPos += 5;
        });

        // Metadata line
        if (msg.tokens || msg.model) {
          doc.setFontSize(7);
          doc.setTextColor(150, 150, 150);
          const metaLine = `${msg.model || 'N/A'} • ${msg.tokens || 0} tokens${msg.cost ? ` • $${msg.cost.toFixed(6)}` : ''}`;
          doc.text(metaLine, margin, yPos);
          yPos += 4;
        }

        yPos += 4; // Spacing between messages

        // Separator line
        doc.setDrawColor(200, 200, 200);
        doc.line(margin, yPos, pageWidth - margin, yPos);
        yPos += 6;
      });
    }

    // Footer on each page
    const totalPages = doc.internal.pages.length - 1;
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(150, 150, 150);
      doc.text(
        `Page ${i} / ${totalPages}`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `conversation-${safeId.slice(0, 8)}-${timestamp}.pdf`;

    doc.save(filename);
    return { success: true, filename };
  } catch (error) {
    throw wrapError(error, 'Impossible d\'exporter le thread en PDF');
  }
}
