"use client";

import Dashboard from "../components/dashboard";
import SellerHome from "../components/seller-home";
import { useWorkspace } from "../lib/workspace";

export default function Home() {
  const { session } = useWorkspace();
  return session.role === "vendedor" ? <SellerHome /> : <Dashboard />;
}
