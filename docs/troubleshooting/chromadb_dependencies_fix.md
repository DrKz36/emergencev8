# Fix ChromaDB 0.5.23 Dependencies Conflict
**Date:** 15 octobre 2025
**Issue:** Backend startup failed with tokenizers version conflicts

## Problem

ChromaDB 0.5.23 upgrade caused dependency conflicts:

```
chromadb 0.5.23 requires tokenizers<=0.20.3,>=0.13.2
transformers 4.55.0 requires tokenizers<0.22,>=0.21
```

**Error message:**
```
sqlite3.OperationalError: no such column: collections.topic
ImportError: tokenizers>=0.21,<0.22 is required for a normal functioning of this module
```

## Root Cause

1. Old vector_store created with ChromaDB 0.4.x
2. New ChromaDB 0.5.23 has different schema (added `collections.topic` column)
3. Tokenizers version incompatibility between ChromaDB 0.5.23 and transformers

## Solution Applied

### 1. Backup & Reset Vector Store
```bash
# Stop all Python processes
taskkill //F //IM python.exe

# Manually backup corrupted vector_store
mv src/backend/data/vector_store src/backend/data/vector_store_backup_manual_$(date +%Y%m%d_%H%M%S)
```

### 2. Fix Dependencies

**Final working versions:**
```
chromadb==0.5.23
tokenizers==0.15.2      # Compatible with both chromadb and transformers 4.38
transformers==4.38.0    # Downgraded from 4.55.0
numpy==1.26.4           # Required for torch compatibility
```

**Installation order:**
```bash
# Install specific versions
pip install 'chromadb==0.5.23'
pip install 'transformers==4.38.0'  # Auto-installs tokenizers 0.15.2
pip install 'numpy==1.26.4'
```

### 3. Verify Installation
```bash
# Test imports
python -c "import chromadb; import sentence_transformers; print('OK')"

# Start backend
pwsh -File scripts/run-backend.ps1
```

## Update requirements.txt

If you need to pin these versions permanently:

```txt
chromadb==0.5.23
transformers==4.38.0  # Compatible with tokenizers 0.15.2 (required by chromadb 0.5.23)
numpy==1.26.4
```

## Verification

After fix, backend startup should show:
```
✅ Modèle SentenceTransformer 'all-MiniLM-L6-v2' chargé (lazy).
✅ Client ChromaDB connecté au répertoire: C:\dev\emergenceV8\src\backend\data\vector_store
✅ VectorService initialisé (lazy) : SBERT + backend CHROMA prêts.
✅ Backend prêt
```

## Alternative Solutions (Not Used)

1. **Upgrade transformers to match tokenizers 0.21+**
   - Would require updating sentence-transformers
   - More risky (potential breaking changes)

2. **Downgrade ChromaDB to 0.4.22**
   - Loses performance improvements in 0.5.23
   - Not compatible with requirements.txt

3. **Use Qdrant instead of ChromaDB**
   - Requires external service
   - More complex setup

## Prevention

1. **Always test dependency upgrades** in isolated environment
2. **Pin critical dependencies** (chromadb, transformers, tokenizers)
3. **Backup vector_store** before upgrades

## Related Files

- `src/backend/features/memory/vector_service.py` - Auto-reset logic for corrupted DB
- `requirements.txt` - Dependency specifications
- `src/backend/data/vector_store/` - ChromaDB persistent storage

---

**Status:** ✅ RESOLVED
**Tested:** 2025-10-15 (Windows 11, Python 3.11)
