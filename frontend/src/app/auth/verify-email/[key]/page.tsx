"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useRef, useState } from "react";
import { AuthCard, authStyles as s } from "@/components/auth/AuthCard";
import { useSession } from "@/lib/session";

export default function VerifyEmailPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const key = decodeURIComponent(use(params).key);
  const { verifyEmail } = useSession();
  const router = useRouter();
  const [state, setState] = useState<"verifying" | "done" | "failed">("verifying");
  const [message, setMessage] = useState("");
  const started = useRef(false);

  useEffect(() => {
    // Keys are single-use; don't submit twice under React strict mode.
    if (started.current) return;
    started.current = true;
    verifyEmail(key).then((result) => {
      if (result.ok) {
        setState("done");
        // New accounts go to their profile to pick a username.
        setTimeout(() => router.replace("/profile"), 1200);
      } else {
        setState("failed");
        setMessage(result.errors?.[0]?.message ?? "This link is invalid or has expired.");
      }
    });
  }, [key, verifyEmail, router]);

  if (state === "verifying") {
    return <AuthCard title="Verifying your email…">{null}</AuthCard>;
  }
  if (state === "done") {
    return (
      <AuthCard title="Email verified">
        <p className={s.notice}>You&apos;re all set. Taking you to your profile…</p>
      </AuthCard>
    );
  }
  return (
    <AuthCard
      title="Couldn't verify email"
      footer={
        <Link href="/auth/sign-in" className={s.link}>
          Go to sign in
        </Link>
      }
    >
      <div className={s.alert} role="alert">
        {message}
      </div>
    </AuthCard>
  );
}
