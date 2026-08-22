"use client";

import { useEffect } from "react";
import { warmBackend } from "@/lib/api";

// Module scope, so a client-side route change doesn't re-ping a backend we've
// already woken during this page load.
let warmed = false;

/**
 * Wakes the backend as soon as anyone lands on the site.
 *
 * Renders nothing. Exists because the free hosting tier sleeps after inactivity
 * and takes ~50s to come back; without this the cold start lands on the first
 * real interaction, which reads as a broken demo rather than a sleeping server.
 */
export function BackendWarmup() {
  useEffect(() => {
    if (warmed) return;
    warmed = true;
    warmBackend();
  }, []);

  return null;
}

export default BackendWarmup;
