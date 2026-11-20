import Link from "next/link";
import { ReactNode } from "react";
import styles from "./auth.module.css";
import type { AuthError } from "@/lib/session";

export { styles as authStyles };

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link href="/" className={styles.brand}>
          Alexandria
        </Link>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        {children}
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>
  );
}

/** Errors not tied to a specific field (allauth sends `param` for field errors). */
export function FormErrors({ errors }: { errors: AuthError[] }) {
  const general = errors.filter((e) => !e.param);
  if (!general.length) return null;
  return (
    <div className={styles.alert} role="alert">
      {general.map((e, i) => (
        <div key={i}>{e.message}</div>
      ))}
    </div>
  );
}

export function Field({
  label,
  name,
  type = "text",
  value,
  onChange,
  errors,
  autoComplete,
  autoFocus,
}: {
  label: string;
  name: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  errors: AuthError[];
  autoComplete?: string;
  autoFocus?: boolean;
}) {
  const fieldErrors = errors.filter((e) => e.param === name);
  const id = `auth-${name}`;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        required
        value={value}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        className={`${styles.input} ${fieldErrors.length ? styles.inputError : ""}`}
        aria-invalid={fieldErrors.length > 0}
        aria-describedby={fieldErrors.length ? `${id}-error` : undefined}
      />
      {fieldErrors.length > 0 && (
        <span id={`${id}-error`} className={styles.fieldError}>
          {fieldErrors.map((e) => e.message).join(" ")}
        </span>
      )}
    </div>
  );
}

/**
 * Only allow redirects to paths inside this app (prevents ?next=https://evil).
 */
export function safeNext(next: string | null, fallback = "/discovery"): string {
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return fallback;
}
