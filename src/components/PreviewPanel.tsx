/* src/components/PreviewPanel.tsx */
import { convertFileSrc, invoke } from "@tauri-apps/api/tauri";
import { useGeneratorStore, HistoryEntry } from "../store/generatorStore";

export function PreviewPanel() {
  const {
    lastResult, previewImagePath, history,
    generating, params, exportImage,
  } = useGeneratorStore();

  const effective = lastResult?.effective_params;

  return (
    <div className="preview-panel">

      {/* Main viewport */}
      <div className="preview-viewport">
        {generating && (
          <div className="preview-overlay">
            <div className="spinner" />
            <span>Generating…</span>
          </div>
        )}

        {previewImagePath && !generating ? (
          <img
            key={previewImagePath}
            src={convertFileSrc(previewImagePath)}
            alt="Generated output"
            className="preview-image"
          />
        ) : !generating ? (
          <div className="preview-empty">
            <div className="preview-empty__icon">◈</div>
            <p className="preview-empty__text">Select a model · press Space to generate</p>
          </div>
        ) : null}
      </div>

      {/* Effective params bar — shows what the route actually used */}
      {lastResult?.ok && !generating && effective && (
        <div className="run-meta-bar">
          <span className="run-meta__item">
            <code>{lastResult.run_id.slice(-8)}</code>
          </span>
          <span className="run-meta__item">
            seed <code>{effective.seed}</code>
          </span>
          <span className="run-meta__item">
            ψ <code>{effective.truncation_psi.toFixed(2)}</code>
          </span>
          <span className="run-meta__item">
            noise <code>{effective.noise_mode}</code>
          </span>
          <span className="run-meta__item run-meta__timing">
            {lastResult.timing_ms}ms
          </span>
          {lastResult.warnings.map((w, i) => (
            <span key={i} className="run-meta__item run-meta__item--warn">⚠ {w}</span>
          ))}
        </div>
      )}

      {/* Error bar */}
      {lastResult?.ok === false && !generating && (
        <div className="run-error-bar">✕ {lastResult.error ?? "Generation failed"}</div>
      )}

      {/* Footer */}
      <div className="preview-footer">
        <button
          className="btn-action"
          disabled={!lastResult?.ok}
          onClick={async () => {
            if (lastResult?.output_image) {
              const folder = lastResult.output_image.substring(0, lastResult.output_image.lastIndexOf("/"));
              await invoke("open_output_folder", { path: folder });
            }
          }}
        >
          Open Folder
        </button>
        <button
          className="btn-action btn-action--primary"
          disabled={!lastResult?.ok}
          onClick={exportImage}
        >
          Export PNG
        </button>
      </div>

      {/* History strip */}
      {history.length > 0 && (
        <div className="history-strip">
          {history.slice(0, 16).map((entry) => (
            <HistoryThumb key={entry.result.run_id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

function HistoryThumb({ entry }: { entry: HistoryEntry }) {
  const { setParam, selectModel, selectRoute } = useGeneratorStore();

  const restore = () => {
    selectModel(entry.model_id);
    selectRoute(entry.route_id);
    setParam("seed", entry.params.seed);
    setParam("truncation_psi", entry.params.truncation_psi);
    setParam("noise_mode", entry.params.noise_mode);
    setParam("mix_seed", entry.params.mix_seed);
    setParam("mix_layers", entry.params.mix_layers);
  };

  const preview = entry.result.preview_image;

  return (
    <button
      className="history-thumb"
      onClick={restore}
      title={`seed ${entry.params.seed} · ψ ${entry.params.truncation_psi.toFixed(2)} · ${entry.route_id}`}
    >
      {preview ? (
        <img src={convertFileSrc(preview)} alt="" className="history-thumb__img" />
      ) : (
        <div className="history-thumb__placeholder">◈</div>
      )}
      <span className="history-thumb__seed">{entry.params.seed}</span>
    </button>
  );
}
