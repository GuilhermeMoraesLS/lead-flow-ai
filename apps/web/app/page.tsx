"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { readSession } from "./lib/api";

export default function Root() {
  const router = useRouter();
  useEffect(() => { router.replace(readSession() ? "/app" : "/entrar"); }, [router]);
  return <div className="boot" aria-busy="true"><span className="spinner" /></div>;
}
