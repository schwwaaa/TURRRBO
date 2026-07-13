/* src/App.tsx */
import { useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { ModelCatalog } from "./components/ModelCatalog";
import { ParameterControls } from "./components/ParameterControls";
import { PreviewPanel } from "./components/PreviewPanel";
import { StatusBar } from "./components/StatusBar";
import { useGeneratorStore } from "./store/generatorStore";
import "./styles/app.css";

export interface BackendStatus {
  healthy: boolean;
  gpu_available: boolean;
  device: string;
  loaded_model: string | null;
  version: string;
}

export default function App() {
  const { setBackendStatus, backendStatus, generate, randomizeSeed, generating } = useGeneratorStore();

  // Poll backend health until ready
  useEffect(() => {
    let stopped = false;
    const check = async () => {
      try {
        const status = await invoke<BackendStatus>("get_backend_status");
        setBackendStatus(status);
        if (status.healthy) return;
      } catch { /* still starting */ }
      if (!stopped) setTimeout(check, 1000);
    };
    check();
    return () => { stopped = true; };
  }, []);

  // Keyboard shortcuts
  const handleKey = useCallback((e: KeyboardEvent) => {
    // Ignore if typing in an input
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLSelectElement ||
      e.target instanceof HTMLTextAreaElement
    ) return;
    // Cmd+Enter or Ctrl+Enter to generate
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (!generating) generate();
    }
    if (e.key === "r" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      randomizeSeed();
    }
  }, [generate, randomizeSeed, generating]);

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-wordmark">TURRRBO</span>
        <span className="app-tagline">stylegan instrument</span>
        <div className="app-shortcuts">
          <span className="shortcut"><kbd>⌘ Enter</kbd> generate</span>
          <span className="shortcut"><kbd>⌘ R</kbd> random seed</span>
        </div>
      </header>

      <div className="app-body">
        <aside className="rail rail--left">
          <ModelCatalog />
        </aside>
        <main className="center-panel">
          <PreviewPanel />
        </main>
        <aside className="rail rail--right">
          <ParameterControls />
        </aside>
      </div>

      <StatusBar />
    </div>
  );
}
