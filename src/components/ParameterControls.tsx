/* src/components/ParameterControls.tsx */
import { useEffect } from "react";
import { useGeneratorStore } from "../store/generatorStore";

export function ParameterControls() {
  const {
    params, setParam, randomizeSeed, randomizeAll,
    generate, generating, selectedModelId,
    styleRoutes, selectedRouteId, loadStyleRoutes, selectRoute,
    templates, loadTemplates, applyTemplate,
    textPrompt, setTextPrompt, clipSteps, setClipSteps, clipLr, setClipLr,
    layerCount, backendStatus,
  } = useGeneratorStore();

  const canGenerate = !!selectedModelId && !generating;

  useEffect(() => {
    if (backendStatus?.healthy) {
      loadStyleRoutes();
      loadTemplates();
    }
  }, [backendStatus?.healthy]);

  const activeRoute = styleRoutes.find((r) => r.id === selectedRouteId);
  const isClipMode = textPrompt.trim().length > 0;

  return (
    <div className="param-controls">
      <div className="rail-header">Controls</div>

      {/* ── Text Prompt ── */}
      <div className="control-group">
        <label className="control-label">
          Text Prompt
          <span className={"control-hint " + (isClipMode ? "hint--active" : "")}>
            {isClipMode ? "CLIP-guided" : "optional"}
          </span>
        </label>
        <textarea
          className={"prompt-input " + (isClipMode ? "prompt-input--active" : "")}
          placeholder="e.g. melting wax face, neon decay, oil spill portrait…"
          value={textPrompt}
          onChange={(e) => setTextPrompt(e.target.value)}
          rows={3}
        />
        {isClipMode && (
          <div className="clip-options">
            <div className="clip-row">
              <span className="clip-label">Steps</span>
              <input type="range" min={10} max={300} step={10}
                value={clipSteps} onChange={(e) => setClipSteps(parseInt(e.target.value))} />
              <span className="slider-value">{clipSteps}</span>
            </div>
            <div className="clip-row">
              <span className="clip-label">LR</span>
              <input type="range" min={0.001} max={0.2} step={0.001}
                value={clipLr} onChange={(e) => setClipLr(parseFloat(e.target.value))} />
              <span className="slider-value">{clipLr.toFixed(3)}</span>
            </div>
            <p className="control-note clip-note">
              CLIP optimizes the latent toward your text. Slower than direct generation.
              Requires CLIP installed.
            </p>
          </div>
        )}
      </div>

      {/* ── Style Route ── */}
      <div className="control-group">
        <label className="control-label">
          Style Route
          <span className="control-hint">Artistic intent</span>
        </label>
        <select className="route-select" value={selectedRouteId}
          onChange={(e) => selectRoute(e.target.value)}>
          {styleRoutes.map((r) => (
            <option key={r.id} value={r.id}>{r.label}</option>
          ))}
        </select>
        {activeRoute && activeRoute.id !== "none" && (
          <p className="control-note">{activeRoute.description}</p>
        )}
        {activeRoute && activeRoute.psi_offset !== 0 && (
          <p className="control-note route-effect">
            ψ {activeRoute.psi_offset > 0 ? "+" : ""}{activeRoute.psi_offset.toFixed(2)} at generation
            {activeRoute.noise_mode_override ? " · noise → " + activeRoute.noise_mode_override : ""}
          </p>
        )}
      </div>

      {/* ── Templates ── */}
      {templates.length > 0 && (
        <div className="control-group">
          <label className="control-label">
            Templates
            <span className="control-hint">Starting points</span>
          </label>
          <div className="template-grid">
            {templates.map((t) => (
              <button key={t.id} className="template-btn" onClick={() => applyTemplate(t)}
                title={t.description}>
                {t.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Seed ── */}
      <div className="control-group">
        <label className="control-label">
          Seed
          <span className="control-hint">Identity</span>
        </label>
        <div className="seed-row">
          <input type="number" className="seed-input" value={params.seed} min={0} max={2147483647}
            onChange={(e) => setParam("seed", parseInt(e.target.value, 10) || 0)} />
          <button className="btn-icon" onClick={randomizeSeed} title="Random seed">⟳</button>
        </div>
      </div>

      {/* ── Truncation ψ ── */}
      <div className="control-group">
        <label className="control-label">
          Truncation ψ
          <span className="control-hint">
            {params.truncation_psi < 0.4 ? "Average" : params.truncation_psi > 1.0 ? "Beyond limit" : params.truncation_psi > 0.85 ? "Extreme" : "Balanced"}
          </span>
        </label>
        <div className="slider-row">
          <input type="range" min={0} max={1.5} step={0.01} value={params.truncation_psi}
            onChange={(e) => setParam("truncation_psi", parseFloat(e.target.value))} />
          <span className="slider-value">{params.truncation_psi.toFixed(2)}</span>
        </div>
        <div className="slider-legend"><span>average</span><span>extreme</span></div>
      </div>

      {/* ── Coarse / Fine PSI split ── */}
      <div className="control-group">
        <label className="control-label">
          Split Truncation
          <span className="control-hint">coarse · fine</span>
        </label>
        <div className="split-psi-row">
          <div className="split-psi-col">
            <span className="split-label">Coarse (0–3)</span>
            <div className="slider-row">
              <input type="range" min={0} max={1.5} step={0.01}
                value={params.coarse_psi ?? params.truncation_psi}
                onChange={(e) => setParam("coarse_psi", parseFloat(e.target.value))} />
              <span className="slider-value">{(params.coarse_psi ?? params.truncation_psi).toFixed(2)}</span>
            </div>
          </div>
          <div className="split-psi-col">
            <span className="split-label">Fine (8+)</span>
            <div className="slider-row">
              <input type="range" min={0} max={1.5} step={0.01}
                value={params.fine_psi ?? params.truncation_psi}
                onChange={(e) => setParam("fine_psi", parseFloat(e.target.value))} />
              <span className="slider-value">{(params.fine_psi ?? params.truncation_psi).toFixed(2)}</span>
            </div>
          </div>
        </div>
        <button className="btn-clear-small"
          onClick={() => { setParam("coarse_psi", null); setParam("fine_psi", null); }}>
          Reset to global ψ
        </button>
      </div>

      {/* ── Noise mode ── */}
      <div className="control-group">
        <label className="control-label">
          Noise Mode
          <span className="control-hint">Surface texture</span>
        </label>
        <div className="btn-group">
          {(["const", "random", "none"] as const).map((mode) => (
            <button key={mode}
              className={"btn-toggle" + (params.noise_mode === mode ? " btn-toggle--active" : "")}
              onClick={() => setParam("noise_mode", mode)}>{mode}</button>
          ))}
        </div>
      </div>

      {/* ── Noise Strength ── */}
      <div className="control-group">
        <label className="control-label">
          Noise Strength
          <span className="control-hint">Surface pressure</span>
        </label>
        <div className="slider-row">
          <input type="range" min={0} max={3} step={0.05} value={params.noise_strength}
            onChange={(e) => setParam("noise_strength", parseFloat(e.target.value))} />
          <span className="slider-value">{params.noise_strength.toFixed(2)}</span>
        </div>
        <div className="slider-legend"><span>silent</span><span>flood</span></div>
      </div>

      {/* ── Style Mixing ── */}
      <div className="control-group">
        <label className="control-label">
          Mix Seed
          <span className="control-hint">Structure donor</span>
        </label>
        <div className="seed-row">
          <input type="number" className="seed-input" placeholder="none"
            value={params.mix_seed ?? ""}
            onChange={(e) => setParam("mix_seed", e.target.value === "" ? null : parseInt(e.target.value, 10))} />
          {params.mix_seed !== null && (
            <button className="btn-icon" onClick={() => setParam("mix_seed", null)}>✕</button>
          )}
        </div>
        {params.mix_seed !== null && (
          <div className="mix-layer-row">
            <span className="split-label">Mix layers (0–{layerCount - 1})</span>
            <div className="layer-range">
              <span className="layer-tag" onClick={() => setParam("mix_layers", [0,1,2,3])}>coarse</span>
              <span className="layer-tag" onClick={() => setParam("mix_layers", [4,5,6,7])}>mid</span>
              <span className="layer-tag" onClick={() => setParam("mix_layers", [8,9,10,11,12,13])}>fine</span>
              <span className="layer-tag" onClick={() => setParam("mix_layers", null)}>all</span>
            </div>
            {params.mix_layers && (
              <p className="control-note">Layers: {params.mix_layers.join(", ")}</p>
            )}
          </div>
        )}
      </div>

      {/* ── Randomize All ── */}
      <div className="control-group">
        <button className="btn-randomize-all" onClick={randomizeAll}>
          ⚄ Randomize Everything
        </button>
      </div>

      {/* ── Generate ── */}
      <div className="generate-section">
        <button
          className={"btn-generate" + (generating ? " btn-generate--busy" : "") + (isClipMode ? " btn-generate--clip" : "")}
          disabled={!canGenerate} onClick={generate}>
          {generating ? (isClipMode ? "CLIP optimizing…" : "Generating…") : (isClipMode ? "Generate (CLIP)" : "Generate")}
        </button>
      </div>
    </div>
  );
}
