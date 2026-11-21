"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { AuthCard, authStyles as s, Field, FormErrors, safeNext } from "@/components/auth/AuthCard";
import { AuthError, useSession } from "@/lib/session";

function SignInForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const { login, isAuthenticated, isLoaded } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<AuthError[]>([]);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isLoaded && isAuthenticated) router.replace(next);
  }, [isLoaded, isAuthenticated, next, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErrors([]);
    const result = await login(email, password);
    setSubmitting(false);
    if (result.ok) {
      router.replace(next);
    } else if (result.pendingEmailVerification) {
      setNeedsVerification(true);
    } else {
      setErrors(result.errors);
    }
  }

  if (needsVerification) {
    return (
      <AuthCard title="Verify your email">
        <p className={s.notice}>
          Your email address hasn&apos;t been verified yet. We&apos;ve sent a new
          link to <strong>{email}</strong>.
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to your Alexandria account"
      footer={
        <>
          New here?{" "}
          <Link href="/auth/sign-up" className={s.link}>
            Create an account
          </Link>
        </>
      }
    >
      <form className={s.form} onSubmit={onSubmit} noValidate>
        <FormErrors errors={errors} />
        <Field label="Email" name="email" type="email" value={email} onChange={setEmail}
          errors={errors} autoComplete="email" autoFocus />
        <Field label="Password" name="password" type="password" value={password}
          onChange={setPassword} errors={errors} autoComplete="current-password" />
        <div className={s.row}>
          <Link href="/auth/forgot-password" className={s.smallLink}>
            Forgot password?
          </Link>
        </div>
        <button type="submit" className={s.button} disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthCard>
  );
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignInForm />
    </Suspense>
  );
}
