import { ReactNode } from "react";
import { SessionProvider } from "@/lib/session";

export function AuthProvider({ children }: { children: ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
