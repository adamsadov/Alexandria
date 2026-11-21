"use client";

import Link from "next/link";
import { FormEvent, use, useState } from "react";
import { AuthCard, authStyles as s, Field, FormErrors } from "@/components/auth/AuthCard";
import { AuthError, useSession } from "@/lib/session";

export default function ResetPasswordPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const key = decodeURIComponent(use(params).key);
  const { resetPassword } = useSession();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<AuthError[]>([]);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErrors([{ message: "Passwords don't match.", param: "confirm" }]);
      return;
    }
    setSubmitting(true);
    setErrors([]);
    const result = await resetPassword(key, password);
    setSubmitting(false);
    if (result.ok) setDone(true);
    else if (result.errors) {
      // A bad/expired key comes back as a "key" field error; show it up top.
      setErrors(result.errors.map((err) => (err.param === "key" ? { message: err.message } : err)));
    }
  }

  if (done) {
    return (
      <AuthCard
        title="Password updated"
        footer={
          <Link href="/auth/sign-in" className={s.link}>
            Sign in with your new password
          </Link>
        }
      >
        <p className={s.notice}>Your password has been changed.</p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
      <form className={s.form} onSubmit={onSubmit} noValidate>
        <FormErrors errors={errors} />
        <Field label="New password" name="password" type="password" value={password}
          onChange={setPassword} errors={errors} autoComplete="new-password" autoFocus />
        <Field label="Confirm new password" name="confirm" type="password" value={confirm}
          onChange={setConfirm} errors={errors} autoComplete="new-password" />
        <button type="submit" className={s.button} disabled={submitting}>
          {submitting ? "Saving…" : "Set new password"}
        </button>
      </form>
    </AuthCard>
  );
}
