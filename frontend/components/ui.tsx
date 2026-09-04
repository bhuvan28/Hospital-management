"use client";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="topbar">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}

export function Banner({ kind, children }: { kind: "error" | "success" | "info"; children: React.ReactNode }) {
  return (
    <div className={`banner ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <label>
        {label}
        {children}
      </label>
      {hint ? <p className="muted" style={{ fontSize: "0.8rem", marginTop: 4 }}>{hint}</p> : null}
    </div>
  );
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="card modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="topbar">
          <h2 id="modal-title">{title}</h2>
          <button className="btn secondary" onClick={onClose} type="button">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Loading({ children = "Loading…" }: { children?: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function ConfirmButton({
  label,
  message,
  onConfirm,
  danger = false,
}: {
  label: string;
  message: string;
  onConfirm: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={danger ? "btn danger" : "btn secondary"}
      onClick={() => {
        if (window.confirm(message)) onConfirm();
      }}
    >
      {label}
    </button>
  );
}
