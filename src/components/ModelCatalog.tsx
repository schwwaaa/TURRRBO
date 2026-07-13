/* src/components/ModelCatalog.tsx */
import { useEffect } from "react";
import { useGeneratorStore } from "../store/generatorStore";

const CATEGORY_LABELS: Record<string, string> = {
  face: "Portraits",
  art: "Art / Painting",
  architecture: "Architecture",
  nature: "Nature",
  abstract: "Abstract",
};

export function ModelCatalog() {
  const { models, selectedModelId, loadModels, selectModel, backendStatus } =
    useGeneratorStore();

  useEffect(() => {
    if (backendStatus?.healthy) {
      loadModels();
    }
  }, [backendStatus?.healthy]);

  const grouped = models.reduce<Record<string, typeof models>>((acc, m) => {
    const cat = m.category || "other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(m);
    return acc;
  }, {});

  return (
    <div className="model-catalog">
      <div className="rail-header">Models</div>

      {models.length === 0 && (
        <div className="empty-state">
          {backendStatus?.healthy ? "No models installed." : "Starting backend…"}
        </div>
      )}

      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat} className="model-group">
          <div className="model-group-label">
            {CATEGORY_LABELS[cat] ?? cat}
          </div>
          {items.map((m) => (
            <button
              key={m.id}
              className={`model-card ${selectedModelId === m.id ? "model-card--active" : ""}`}
              onClick={() => selectModel(m.id)}
            >
              <span className="model-card__name">{m.name}</span>
              <span className="model-card__res">{m.resolution}px</span>
              <p className="model-card__desc">{m.description}</p>
              <div className="model-card__tags">
                {m.tags.slice(0, 3).map((t) => (
                  <span key={t} className="tag">{t}</span>
                ))}
              </div>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
