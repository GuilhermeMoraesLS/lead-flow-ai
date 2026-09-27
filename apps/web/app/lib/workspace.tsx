"use client";

import { createContext, useContext } from "react";
import type { Operation, Session } from "./api";

export type Workspace = {
  session: Session;
  /** Loaded for gestores only; sellers do not read the operation. */
  operation: Operation | null;
  reloadOperation: () => Promise<void>;
  /** Ends the session and returns to the sign-in screen with the given reason. */
  expire: (message: string) => void;
  signOut: () => void;
};

export const WorkspaceContext = createContext<Workspace | null>(null);

export function useWorkspace() {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("useWorkspace must be used inside the app shell.");
  return workspace;
}
