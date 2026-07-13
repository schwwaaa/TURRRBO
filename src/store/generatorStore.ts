/* src/store/generatorStore.ts */
import { create } from "zustand";
import { invoke } from "@tauri-apps/api/tauri";
import type { BackendStatus } from "../App";

export interface ModelInfo {
  id: string; name: string; description: string; resolution: number;
  category: string; provenance: string; checkpoint_file: string;
  recommended_psi: number; tags: string[];
}

export interface StyleRoute {
  id: string; label: string; description: string;
  psi_offset: number; noise_mode_override: string | null; mix_layer_preset: number[] | null;
}

export interface Template {
  id: string; name: string; description: string; model_hint: string | null;
  params: StyleGANParams; style_route: string; text_prompt: string | null;
}

export interface StyleGANParams {
  seed: number;
  truncation_psi: number;
  noise_mode: "const" | "random" | "none";
  mix_seed: number | null;
  mix_layers: number[] | null;
  layer_weights: number[] | null;
  noise_strength: number;
  coarse_psi: number | null;
  fine_psi: number | null;
}

export interface GenerateResult {
  ok: boolean; output_image: string | null; preview_image: string | null;
  model_id: string; run_id: string; timing_ms: number; warnings: string[];
  error: string | null; effective_params: StyleGANParams | null; clip_guided: boolean;
}

export interface HistoryEntry {
  result: GenerateResult; params: StyleGANParams; model_id: string;
  route_id: string; text_prompt: string; timestamp: number;
}

interface GeneratorStore {
  backendStatus: BackendStatus | null;
  setBackendStatus: (s: BackendStatus) => void;

  models: ModelInfo[];
  selectedModelId: string | null;
  loadModels: () => Promise<void>;
  selectModel: (id: string) => void;

  styleRoutes: StyleRoute[];
  selectedRouteId: string;
  loadStyleRoutes: () => Promise<void>;
  selectRoute: (id: string) => void;

  templates: Template[];
  loadTemplates: () => Promise<void>;
  applyTemplate: (t: Template) => void;

  layerCount: number;
  loadLayerCount: (modelId: string) => Promise<void>;

  params: StyleGANParams;
  textPrompt: string;
  clipSteps: number;
  clipLr: number;
  setParam: <K extends keyof StyleGANParams>(key: K, value: StyleGANParams[K]) => void;
  setTextPrompt: (t: string) => void;
  setClipSteps: (n: number) => void;
  setClipLr: (n: number) => void;
  randomizeSeed: () => void;
  randomizeAll: () => void;

  generating: boolean;
  lastResult: GenerateResult | null;
  history: HistoryEntry[];
  previewImagePath: string | null;
  generate: () => Promise<void>;
  exportImage: () => Promise<void>;
}

export const DEFAULT_PARAMS: StyleGANParams = {
  seed: 0, truncation_psi: 0.7, noise_mode: "const",
  mix_seed: null, mix_layers: null, layer_weights: null,
  noise_strength: 1.0, coarse_psi: null, fine_psi: null,
};

const NOISE_MODES: StyleGANParams["noise_mode"][] = ["const", "random", "none"];

export const useGeneratorStore = create<GeneratorStore>((set, get) => ({
  backendStatus: null,
  setBackendStatus: (s) => set({ backendStatus: s }),

  models: [], selectedModelId: null,
  loadModels: async () => {
    try {
      const models = await invoke<ModelInfo[]>("list_models");
      set({ models });
      if (models.length > 0 && !get().selectedModelId) {
        const first = models[0];
        set({ selectedModelId: first.id,
              params: { ...DEFAULT_PARAMS, truncation_psi: first.recommended_psi } });
        get().loadLayerCount(first.id);
      }
    } catch (e) { console.error("list_models failed:", e); }
  },
  selectModel: (id) => {
    const model = get().models.find((m) => m.id === id);
    set({ selectedModelId: id,
          params: { ...get().params, truncation_psi: model?.recommended_psi ?? 0.7 } });
    get().loadLayerCount(id);
  },

  styleRoutes: [], selectedRouteId: "none",
  loadStyleRoutes: async () => {
    try { set({ styleRoutes: await invoke<StyleRoute[]>("list_style_routes") }); }
    catch (e) { console.error("list_style_routes failed:", e); }
  },
  selectRoute: (id) => set({ selectedRouteId: id }),

  templates: [],
  loadTemplates: async () => {
    try { set({ templates: await invoke<Template[]>("list_templates") }); }
    catch (e) { console.error("list_templates failed:", e); }
  },
  applyTemplate: (t) => {
    // Never overwrite the text prompt — user typed it intentionally
    set({ params: { ...DEFAULT_PARAMS, ...t.params },
          selectedRouteId: t.style_route });
    if (t.model_hint) {
      const match = get().models.find((m) => m.category === t.model_hint);
      if (match) set({ selectedModelId: match.id });
    }
  },

  layerCount: 18,
  loadLayerCount: async (modelId) => {
    try {
      const count = await invoke<number>("get_layer_count", { modelId });
      set({ layerCount: count });
    } catch { set({ layerCount: 18 }); }
  },

  params: DEFAULT_PARAMS,
  textPrompt: "", clipSteps: 80, clipLr: 0.05,
  setParam: (key, value) => set((s) => ({ params: { ...s.params, [key]: value } })),
  setTextPrompt: (t) => set({ textPrompt: t }),
  setClipSteps: (n) => set({ clipSteps: n }),
  setClipLr: (n) => set({ clipLr: n }),

  randomizeSeed: () =>
    set((s) => ({ params: { ...s.params, seed: Math.floor(Math.random() * 2 ** 31) } })),

  randomizeAll: () => {
    const routes = get().styleRoutes;
    const randomRoute = routes.length > 0
      ? routes[Math.floor(Math.random() * routes.length)].id
      : "none";
    const modes: StyleGANParams["noise_mode"][] = ["const", "random", "none"];
    set({
      params: {
        seed: Math.floor(Math.random() * 2 ** 31),
        truncation_psi: Math.random() * 1.2 + 0.1,
        noise_mode: modes[Math.floor(Math.random() * modes.length)],
        mix_seed: Math.random() > 0.6 ? Math.floor(Math.random() * 2 ** 31) : null,
        mix_layers: null,
        layer_weights: null,
        noise_strength: Math.random() * 1.5 + 0.3,
        coarse_psi: Math.random() > 0.6 ? Math.random() * 1.2 : null,
        fine_psi: Math.random() > 0.6 ? Math.random() * 1.4 : null,
      },
      selectedRouteId: randomRoute,
    });
  },

  generating: false, lastResult: null, history: [], previewImagePath: null,

  generate: async () => {
    const { selectedModelId, params, history, selectedRouteId, textPrompt, clipSteps, clipLr } = get();
    if (!selectedModelId) return;
    set({ generating: true });
    try {
      const result = await invoke<GenerateResult>("generate_image", {
        request: {
          model_id: selectedModelId, params,
          style_route: selectedRouteId,
          text_prompt: textPrompt.trim() || null,
          clip_steps: clipSteps, clip_lr: clipLr,
          output_dir: null, session_note: null,
        },
      });
      set({
        lastResult: result, previewImagePath: result.preview_image,
        history: [{ result, params: { ...params }, model_id: selectedModelId,
                    route_id: selectedRouteId, text_prompt: textPrompt, timestamp: Date.now() },
                  ...history].slice(0, 50),
      });
    } catch (e) {
      set({ lastResult: { ok: false, output_image: null, preview_image: null,
        model_id: selectedModelId ?? "", run_id: "", timing_ms: 0, warnings: [],
        error: String(e), effective_params: null, clip_guided: false } });
    } finally { set({ generating: false }); }
  },

  exportImage: async () => {
    const { lastResult } = get();
    if (!lastResult?.output_image) return;
    try { await invoke("export_image", { sourcePath: lastResult.output_image }); }
    catch (e) { console.error("Export failed:", e); }
  },
}));
