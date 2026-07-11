import { useEffect, useRef } from "react";
import { useAgentStore } from "../stores/agent-store";

const WS_URL = "ws://localhost:8420/api/ws";
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];

/**
 * Connects to the Edge Agent WebSocket and pushes real-time events
 * into the Zustand agent store. Auto-reconnects with exponential backoff.
 *
 * Protocol:
 *   Server → Client: {"type":"event","event":{...}}   (real-time push)
 *   Server → Client: {"type":"events","events":[...]}  (buffered on connect)
 *   Server → Client: {"type":"ping"}                   (keepalive, 30s)
 *   Client → Server: {"type":"pong"}                   (keepalive response)
 */
export function useAgentWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          attemptRef.current = 0;
          useAgentStore.setState({ wsConnected: true });
        };

        ws.onmessage = (msg) => {
          try {
            const data = JSON.parse(msg.data) as {
              type: string;
              event?: Record<string, unknown>;
              events?: Record<string, unknown>[];
            };

            // Server keepalive — respond with pong
            if (data.type === "ping") {
              ws.send(JSON.stringify({ type: "pong" }));
              return;
            }

            // Normalize to an array of events
            const eventList =
              data.type === "events"
                ? data.events || []
                : data.type === "event" && data.event
                  ? [data.event]
                  : [];

            for (const evt of eventList) {
              handleAgentEvent(evt);
            }
          } catch {
            // ignore malformed messages
          }
        };

        ws.onclose = () => {
          useAgentStore.setState({ wsConnected: false });
          wsRef.current = null;
          scheduleReconnect();
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        scheduleReconnect();
      }
    }

    function scheduleReconnect() {
      if (!mountedRef.current) return;
      const delay =
        RECONNECT_DELAYS[
          Math.min(attemptRef.current, RECONNECT_DELAYS.length - 1)
        ];
      attemptRef.current++;
      reconnectRef.current = setTimeout(connect, delay);
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, []);
}

/** Route an agent event to the appropriate store action. */
function handleAgentEvent(evt: Record<string, unknown>) {
  const store = useAgentStore.getState();
  const eventType = evt?.type as string | undefined;
  if (!eventType) return;

  switch (eventType) {
    // ── Scan ────────────────────────────────────────────────────────────
    case "scan_completed":
    case "scan_failed": {
      // Remove from processingFiles if we have the fileId
      const fileId = evt.file_id as string | undefined;
      if (fileId) {
        const current = store.processingFiles;
        if (current.has(fileId)) {
          const updated = new Set(current);
          updated.delete(fileId);
          useAgentStore.setState({ processingFiles: updated });
        }
      }
      store.fetchFiles();
      break;
    }

    // ── File changes ────────────────────────────────────────────────────
    case "file_created":
    case "file_deleted":
    case "file_modified":
      store.fetchFiles();
      break;

    // ── Agent status ────────────────────────────────────────────────────
    case "status_changed":
      store.fetchStatus();
      break;

    // ── Metrics ─────────────────────────────────────────────────────────
    case "metrics_updated":
      store.fetchMetrics();
      break;

    // ── Sync ────────────────────────────────────────────────────────────
    case "sync_completed":
      store.fetchFiles();
      break;

    default:
      break;
  }
}
