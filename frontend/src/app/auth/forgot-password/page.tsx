"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AuthCard, authStyles as s, Field, FormErrors } from "@/components/auth/AuthCard";
import { AuthError, useSession } from "@/lib/session";

export default function ForgotPasswordPage() {
  const { requestPasswordReset } = useSession();
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<AuthError[]>([]);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErrors([]);
    const result = await requestPasswordReset(email);
    setSubmitting(false);
    if (result.ok) setSent(true);
    else if (result.errors) setErrors(result.errors);
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle={sent ? undefined : "Enter your email and we'll send you a reset link."}
      footer={
        <Link href="/auth/sign-in" className={s.link}>
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <p className={s.notice}>
          If an account exists for <strong>{email}</strong>, a reset link is on
          its way.
        </p>
      ) : (
        <form className={s.form} onSubmit={onSubmit} noValidate>
          <FormErrors errors={errors} />
          <Field label="Email" name="email" type="email" value={email} onChange={setEmail}
            errors={errors} autoComplete="email" autoFocus />
          <button type="submit" className={s.button} disabled={submitting}>
            {submitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthCard>
  );
}
