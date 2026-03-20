/**
 * IndexedDB persistence helpers for uploaded PDF bytes.
 *
 * Story 12.4 — Persists PDF bytes across page refreshes so PDFReference.vue
 * can restore them without requiring a new upload or a live server endpoint.
 *
 * Key schema: `${jobId}-${index}` → Uint8Array
 */

import { openDB, type IDBPDatabase } from 'idb'

const DB_NAME = 'migrador-pdfs'
const STORE_NAME = 'pdfs'
const DB_VERSION = 1

async function getDb(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    },
  })
}

/**
 * Persist PDF bytes for a given job and index.
 * Silently swallows errors — IndexedDB failure must not block the upload flow.
 */
export async function savePdfBytes(
  jobId: string,
  index: number,
  bytes: Uint8Array,
): Promise<void> {
  try {
    const db = await getDb()
    await db.put(STORE_NAME, bytes, `${jobId}-${index}`)
  } catch {
    // Non-fatal: IndexedDB may be unavailable in some environments
  }
}

/**
 * Retrieve previously persisted PDF bytes.
 * Returns null when not found or on any error.
 */
export async function loadPdfBytes(
  jobId: string,
  index: number,
): Promise<Uint8Array | null> {
  try {
    const db = await getDb()
    const result = await db.get(STORE_NAME, `${jobId}-${index}`)
    return result ?? null
  } catch {
    return null
  }
}

/**
 * Remove all persisted PDF bytes for a given job (called on job expiry / new upload).
 * Uses a prefix scan since IDB doesn't natively support prefix deletes.
 */
export async function clearPdfBytes(jobId: string): Promise<void> {
  try {
    const db = await getDb()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const keys = await store.getAllKeys()
    const prefix = `${jobId}-`
    for (const key of keys) {
      if (typeof key === 'string' && key.startsWith(prefix)) {
        await store.delete(key)
      }
    }
    await tx.done
  } catch {
    // Non-fatal
  }
}
