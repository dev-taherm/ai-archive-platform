"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";

// Event types received from the SaaS backend
interface DashboardEvent {
  type: string;
  data: Record<string, unknown>;
}

interface UseDashboardWSOptions {
  onAgentStatusChanged?: (data: Record<string, unknown>) => void;
  onFilesSynced?: (data: Record<string, unknown>) => void;
  onDocumentUpdate?: (data: Record<string, unknown>) => void;
  onProcessingUpdate?: (data: Record<string, unknown>) => void;
}

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];

/**
 * Connects to the SaaS backend WebSocket for real-time dashboard updates.
 *
 * Receives:
 *  - agent_status_changed  (from AgentConsumer._notify_dashboard)
 *  - files_synced           (from AgentConsumer._handle_sync_files)
 *  - document_update        (from DashboardConsumer.document_update)
 *  - processing_update      (from ProcessingConsumer.processing_update)
 *
 * Requires a valid JWT access token stored in useAuthStore.
 */
export function useDashboardWS(callbacks: UseDashboardWSOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  // Reactive connection state
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    const { accessToken, isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated || !accessToken) return;

    // Derive WS URL from API base URL
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let wsBase = apiBase.replace(/^http/, "ws");
    if (!wsBase.endsWith("/")) wsBase += "/";
    const url = `${wsBase}ws/dashboard?token=${encodeURIComponent(accessToken)}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[DashboardWS] Connected");
        reconnectAttempt.current = 0;
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as DashboardEvent;
          const cbs = callbacksRef.current;
          switch (msg.type) {
            case "agent_status_changed":
              cbs.onAgentStatusChanged?.(msg.data);
              break;
            case "files_synced":
              cbs.onFilesSynced?.(msg.data);
              break;
            case "document_update":
              cbs.onDocumentUpdate?.(msg.data);
              break;
            case "processing_update":
              cbs.onProcessingUpdate?.(msg.data);
              break;
            default:
              break;
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = (event) => {
        console.log("[DashboardWS] Disconnected", event.code);
        wsRef.current = null;
        setIsConnected(false);
        // Auto-reconnect unless explicitly closed
        if (event.code !== 1000) {
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      scheduleReconnect();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimer.current) return;
    const delay =
      RECONNECT_DELAYS[
        Math.min(reconnectAttempt.current, RECONNECT_DELAYS.length - 1)
      ];
    reconnectAttempt.current++;
    reconnectTimer.current = setTimeout(() => {
      reconnectTimer.current = null;
      connect();
    }, delay);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close(1000);
    };
  }, [connect]);

  return { isConnected };
}
