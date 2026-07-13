/* src/components/StatusBar.tsx */
import { useGeneratorStore } from "../store/generatorStore";

export function StatusBar() {
  const { backendStatus, selectedModelId, models } = useGeneratorStore();
  const model = models.find((m) => m.id === selectedModelId);

  return (
    <footer className="status-bar">
      <div className="status-bar__left">
        <span
          className={`status-dot ${
            backendStatus?.healthy ? "status-dot--ok" : "status-dot--waiting"
          }`}
        />
        <span className="status-text">
          {backendStatus?.healthy
            ? `backend ready · ${backendStatus.device.toUpperCase()}`
            : "starting backend…"}
        </span>
      </div>

      <div className="status-bar__center">
        {model && (
          <span className="status-model">
            {model.name} · {model.resolution}px
          </span>
        )}
      </div>

      <div className="status-bar__right">
        <span className="status-version">TURRRBO v0.1</span>
      </div>
    </footer>
  );
}
