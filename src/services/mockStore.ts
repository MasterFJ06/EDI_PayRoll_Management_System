import { mockDelay } from "./api";

/**
 * Small localStorage-backed store used by the frontend demo. It makes CRUD
 * interactions survive page refreshes while keeping the API boundary ready
 * for the real FastAPI services.
 */
export function createMockStore<T extends { id: string }>(seed: T[], storageKey?: string) {
  const key = `epms_store_${storageKey ?? seed[0]?.id ?? "data"}`;
  let items: T[] = load();

  function load(): T[] {
    try {
      const raw = localStorage.getItem(key);
      if (raw) return JSON.parse(raw) as T[];
    } catch {
      // Fall back to the seed if storage is unavailable/corrupt.
    }
    return [...seed];
  }

  function persist() {
    try { localStorage.setItem(key, JSON.stringify(items)); } catch { /* demo mode */ }
  }

  return {
    list: async (): Promise<T[]> => mockDelay([...items]),
    get: async (id: string): Promise<T | undefined> => mockDelay(items.find((i) => i.id === id)),
    create: async (item: T): Promise<T> => {
      items = [item, ...items];
      persist();
      return mockDelay(item);
    },
    update: async (id: string, patch: Partial<T>): Promise<T | undefined> => {
      items = items.map((i) => (i.id === id ? { ...i, ...patch } : i));
      persist();
      return mockDelay(items.find((i) => i.id === id));
    },
    remove: async (id: string): Promise<void> => {
      items = items.filter((i) => i.id !== id);
      persist();
      return mockDelay(undefined);
    },
    replaceAll: (next: T[]) => { items = next; persist(); },
    reset: () => { items = [...seed]; persist(); },
  };
}
