// Teams JS SDK wrapper: identity + theme from the Teams context, with a plain-browser fallback.
import { app } from "@microsoft/teams-js";

export type TeamsInfo = { inTeams: boolean; userId: string; userName: string; theme: "light" | "dark" | "contrast" };

const FALLBACK: TeamsInfo = { inTeams: false, userId: "", userName: "", theme: "light" };

function formatNameFromId(idOrEmail: string): string {
  const base = idOrEmail.split("@")[0].trim();
  return base
    .split(/[._-]+/)
    .filter(Boolean)
    .map((p) => (p.length === 1 ? p.toUpperCase() : p[0].toUpperCase() + p.slice(1).toLowerCase()))
    .join(" ") || idOrEmail;
}

function mapTheme(t?: string): TeamsInfo["theme"] {
  if (t === "dark") return "dark";
  if (t === "contrast") return "contrast";
  return "light";
}

export async function initTeams(onTheme: (t: TeamsInfo["theme"]) => void): Promise<TeamsInfo> {
  try {
    await Promise.race([app.initialize(), new Promise((_, rej) => setTimeout(() => rej(new Error("not in Teams")), 1500))]);
    const ctx = await app.getContext();
    app.registerOnThemeChangeHandler((t) => onTheme(mapTheme(t)));
    app.notifySuccess();
    const upn = ctx.user?.userPrincipalName || ctx.user?.loginHint || "";
    const userId = (upn.split("@")[0] || ctx.user?.id || FALLBACK.userId).toLowerCase();
    const rawName = ctx.user?.displayName?.trim();
    const userName = rawName && !rawName.includes("@") ? rawName : formatNameFromId(upn || userId);
    return { inTeams: true, userId, userName, theme: mapTheme(ctx.app?.theme) };
  } catch {
    const asUser = new URLSearchParams(window.location.search).get("as")?.trim().toLowerCase();
    if (asUser) {
      return { ...FALLBACK, userId: asUser, userName: formatNameFromId(asUser) };
    }
    return FALLBACK;
  }
}
