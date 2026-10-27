"use client";

import { cloneElement, isValidElement, useEffect, useId, useRef } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="topbar">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="header-actions">{actions}</div> : null}
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
  const autoId = useId();
  const childId = isValidElement(children) ? ((children.props as { id?: string }).id || autoId) : autoId;
  const control = isValidElement(children)
    ? cloneElement(children as React.ReactElement<{ id?: string }>, { id: childId })
    : children;
  return (
    <div>
      <label htmlFor={childId}>{label}</label>
      {control}
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
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = dialogRef.current;
    const firstField = root?.querySelector<HTMLElement>("input, select, textarea");
    (firstField || root)?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onCloseRef.current();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="modal-backdrop" onClick={() => onCloseRef.current()} role="presentation">
      <div
        className="card modal"
        ref={dialogRef}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        <div className="topbar">
          <h2 id="modal-title">{title}</h2>
          <button className="btn secondary" onClick={() => onCloseRef.current()} type="button">
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
  return (
    <div className="empty" role="status" aria-live="polite">
      {children}
    </div>
  );
}

export function ConfirmButton({
  label,
  message,
  onConfirm,
  danger = false,
}: {
  label: string;
  message: string;
  onConfirm: () => void | Promise<void>;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={danger ? "btn danger" : "btn secondary"}
      onClick={() => {
        if (window.confirm(message)) void onConfirm();
      }}
    >
      {label}
    </button>
  );
}
