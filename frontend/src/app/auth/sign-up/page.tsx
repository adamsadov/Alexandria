"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthCard, authStyles as s, Field, FormErrors } from "@/components/auth/AuthCard";
import { AuthError, useSession } from "@/lib/session";

export default function SignUpPage() {
  const router = useRouter();
  const { signup, isAuthenticated, isLoaded } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<AuthError[]>([]);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isLoaded && isAuthenticated) router.replace("/discovery");
  }, [isLoaded, isAuthenticated, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErrors([{ message: "Passwords don't match.", param: "confirm" }]);
      return;
    }
    setSubmitting(true);
    setErrors([]);
    const result = await signup(email, password);
    setSubmitting(false);
    if (result.ok) {
      // Email verification is turned off: the user is already signed in.
      router.replace("/profile");
    } else if (result.pendingEmailVerification) {
      setSentTo(email);
    } else {
      setErrors(result.errors);
    }
  }

  if (sentTo) {
    return (
      <AuthCard title="Check your email">
        <p className={s.notice}>
          We sent a verification link to <strong>{sentTo}</strong>. Open it to
          finish creating your account.
        </p>
        {process.env.NODE_ENV !== "production" && (
          <p className={s.footer}>
            Local development: the email is printed in the Django server&apos;s
            terminal.
          </p>
        )}
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Track your reading, join book clubs, and share reviews."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/auth/sign-in" className={s.link}>
            Sign in
          </Link>
        </>
      }
    >
      <form className={s.form} onSubmit={onSubmit} noValidate>
        <FormErrors errors={errors} />
        <Field label="Email" name="email" type="email" value={email} onChange={setEmail}
          errors={errors} autoComplete="email" autoFocus />
        <Field label="Password" name="password" type="password" value={password}
          onChange={setPassword} errors={errors} autoComplete="new-password" />
        <Field label="Confirm password" name="confirm" type="password" value={confirm}
          onChange={setConfirm} errors={errors} autoComplete="new-password" />
        <button type="submit" className={s.button} disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthCard>
  );
}
