"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

/** /profile -> /profile/<your user id> */
export default function ProfileRedirect() {
  const router = useRouter();
  const { user, isLoaded } = useSession();

  useEffect(() => {
    if (!isLoaded) return;
    if (user) router.replace(`/profile/${user.id}`);
    else router.replace("/auth/sign-in?next=/profile");
  }, [user, isLoaded, router]);

  return (
    <div className="min-h-screen bg-amber-50 flex items-center justify-center">
      <div className="text-amber-800 text-xl">Loading your profile...</div>
    </div>
  );
}
