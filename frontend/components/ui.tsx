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
  return <div className={`banner ${kind}`}>{children}</div>;
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label>{label}</label>
      {children}
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
    <div className="modal-backdrop" onClick={onClose}>
      <div className="card modal" onClick={(event) => event.stopPropagation()}>
        <div className="topbar">
          <h2>{title}</h2>
          <button className="btn secondary" onClick={onClose}>
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
      className={danger ? "btn danger" : "btn secondary"}
      onClick={() => {
        if (window.confirm(message)) onConfirm();
      }}
    >
      {label}
    </button>
  );
}
