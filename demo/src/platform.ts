import { createContext, useContext } from "react";

// Which system this cut of the video is for. The landing page plays the cut
// that matches the visitor's computer, so a Mac visitor sees a Mac and the
// Mac hotkey. The square LinkedIn cut is the Windows one.

export type Platform = "windows" | "mac" | "linux";
export const PLATFORMS: Platform[] = ["windows", "mac", "linux"];

export const PlatformContext = createContext<Platform>("windows");
export const usePlatform = () => useContext(PlatformContext);

// Each system's default hotkey (uniqr/hotkeys.py and shell_portable.py).
export const HOTKEY: Record<Platform, string[]> = {
  windows: ["Win", "Shift", "Q"],
  mac: ["Cmd", "Shift", "8"],
  linux: ["Ctrl", "Alt", "Q"],
};
export const useHotkey = () => HOTKEY[usePlatform()];
