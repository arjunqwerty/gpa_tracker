// Talking to the backend. Every call goes to /api/... (proxied to port 8000 in development).
import { useCallback, useEffect, useState } from "react";
import type { Curriculum, ProfileData } from "./types";

const TIMEOUT_MS = 30_000;

async function errorMessage(response: Response): Promise<string> {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{loc: ["body", "credits"], msg: "..."}]
      return detail.map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`).join("; ");
    }
  } catch {
    // not JSON - fall through
  }
  if (response.status >= 500) {
    return "The server ran into a problem and nothing was changed. Try again; if it keeps happening, check the backend log.";
  }
  return `The request failed (${response.status} ${response.statusText}). Try again.`;
}

/** fetch() that turns "offline" and "took too long" into messages a person can act on. */
async function fetchOrExplain(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, { ...init, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (error) {
    if ((error as Error).name === "TimeoutError") {
      throw new Error("The server took too long to answer. Check your connection and try again.");
    }
    throw new Error("Can't reach the server. Check your internet connection, or whether the backend is running, and try again.");
  }
}

// Login lives in two httpOnly cookies (see backend/app/security.py): a 15-minute access
// cookie and a refresh cookie that renews it. JavaScript never sees either.

/** Called when the session has ended and cannot be renewed. AuthProvider sets it. */
export const session = { onEnded: () => {} };

let renewing: Promise<boolean> | null = null;

/** Gets a fresh access cookie. Simultaneous callers share one request. */
export function renewSession(): Promise<boolean> {
  renewing ??= fetch("/api/auth/refresh", { method: "POST" })
    .then((response) => response.ok)
    .finally(() => (renewing = null));
  return renewing;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData;
  const send = () =>
    fetchOrExplain(path, {
      method,
      headers: body === undefined || isForm ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });

  let response = await send();
  const renewable = !path.startsWith("/api/auth/") || path === "/api/auth/me";
  if (response.status === 401 && renewable) {
    await renewSession();
    response = await send(); // retried even if renewing failed: another tab may have renewed the cookie
    if (response.status === 401) session.onEnded();
  }
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  delete: <T = void>(path: string) => request<T>("DELETE", path),
};

/** Loads `path` (skipped when null) and reloads it whenever `reload()` is called. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    setError(undefined);
    api
      .get<T>(path)
      .then((result) => !cancelled && setData(result))
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, reload };
}

/** Runs a save/delete action, keeping its error message and busy flag for the UI. */
export function useAction() {
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(undefined);
    try {
      await action();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  return { run, error, busy };
}

/** The curriculum selected in the user's profile (categories and course templates). */
export function useCurriculum() {
  const profile = useApi<ProfileData>("/api/profile");
  const id = profile.data?.profile.curriculum_version_id;
  return useApi<Curriculum>(id ? `/api/curricula/${id}` : null);
}
