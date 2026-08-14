"use client";

import { useSyncExternalStore } from "react";

export type ExperienceMode = "standard" | "advanced";

const storageKey = "personal-ai-os:experience-mode";
const modeChangedEvent = "personal-ai-os:experience-mode-changed";

function getMode(): ExperienceMode {
  if (typeof window === "undefined") return "standard";
  return window.localStorage.getItem(storageKey) === "advanced" ? "advanced" : "standard";
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(modeChangedEvent, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(modeChangedEvent, callback);
  };
}

export function setExperienceMode(mode: ExperienceMode) {
  window.localStorage.setItem(storageKey, mode);
  window.dispatchEvent(new Event(modeChangedEvent));
}

export function useExperienceMode() {
  return useSyncExternalStore(subscribe, getMode, () => "standard" as ExperienceMode);
}
