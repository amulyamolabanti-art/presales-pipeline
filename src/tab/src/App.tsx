import { useCallback, useEffect, useState } from "react";
import { Avatar, Button, FluentProvider, Spinner, Toast, ToastBody, Toaster, ToastTitle, teamsDarkTheme, teamsHighContrastTheme, teamsLightTheme, useId, useToastController } from "@fluentui/react-components";
import { AddRegular, WeatherMoonRegular, WeatherSunnyRegular } from "@fluentui/react-icons";
import { api, setIdentity, type Meta } from "./api";
import { initTeams, type TeamsInfo } from "./teams";
import { ProposalsPage } from "./pages/ProposalsPage";
import { Workspace } from "./pages/Workspace";

export default function App() {
  const [teams, setTeams] = useState<TeamsInfo | null>(null);
  const [theme, setTheme] = useState<TeamsInfo["theme"]>("light");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState("");
  // Deep link support: ?proposal=<id>&tab=<Overview|Scope|...> (also what a Teams subEntityId will map to).
  const params = new URLSearchParams(window.location.search);
  const [proposalId, setProposalId] = useState<string | null>(() => params.get("proposal") || sessionStorage.getItem("apa.proposal"));
  const [pickerMode, setPickerMode] = useState<"new" | "existing" | undefined>(undefined);
  const initialTab = params.get("tab") || "Summary";
  const toasterId = useId("toaster");
  const { dispatchToast } = useToastController(toasterId);

  const notify = useCallback((text: string, kind: "ok" | "err" = "ok") => {
    dispatchToast(
      <Toast><ToastTitle>{kind === "ok" ? "Done" : "Problem"}</ToastTitle><ToastBody>{text}</ToastBody></Toast>,
      { intent: kind === "ok" ? "success" : "error", timeout: kind === "ok" ? 3500 : 8000 },
    );
  }, [dispatchToast]);

  useEffect(() => {
    initTeams(setTheme).then(async (t) => {
      setTeams(t);
      const forced = params.get("theme");
      setTheme(forced === "dark" || forced === "light" || forced === "contrast" ? forced : t.theme);
      if (t.userId) {
        setIdentity(t.userId, t.userName);
      }
      const m = await api.meta();
      setMeta(m);
      if (m?.user) {
        setIdentity(m.user.user_id, m.user.display_name);
      }
      if (!params.get("proposal") && !sessionStorage.getItem("apa.proposal")) {
        const mine = await api.proposals();
        if (mine.length === 1) {
          sessionStorage.setItem("apa.proposal", mine[0].proposal_id);
          setProposalId(mine[0].proposal_id);
        }
      }
    }).catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const open = (id: string) => { setPickerMode(undefined); sessionStorage.setItem("apa.proposal", id); setProposalId(id); };
  const close = () => { setPickerMode(undefined); sessionStorage.removeItem("apa.proposal"); setProposalId(null); };
  const startNew = () => { setPickerMode("new"); sessionStorage.removeItem("apa.proposal"); setProposalId(null); };

  const fluentTheme = theme === "dark" ? teamsDarkTheme : theme === "contrast" ? teamsHighContrastTheme : teamsLightTheme;
  const dark = theme !== "light";

  return (
    <FluentProvider theme={fluentTheme} className={"provider" + (dark ? " theme-dark" : "")}>
      <Toaster toasterId={toasterId} position="top-end" />
      {meta && (() => {
        const isUnknown = (!teams?.inTeams && !teams?.userId) || !meta.user.user_id || meta.user.user_id.toLowerCase() === "unknown" || meta.user.display_name.toLowerCase() === "unknown";
        const displayName = isUnknown ? "Unknown" : meta.user.display_name;
        const dept = isUnknown ? "" : (meta.user.department || "");
        return (
          <header className="app-topbar">
            <div className="app-topbar-inner">
              <div className="app-brand">AI Proposal Assistant</div>
              <span className="spacer" />
              <div className="user-pill" title={isUnknown ? "Unknown User (outside Teams)" : `${displayName} (${meta.user.user_id})`}>
                <Avatar name={isUnknown ? "Unknown" : displayName} color={isUnknown ? "neutral" : "brand"} size={32} />
                <div className="user-meta">
                  <div className="user-name">{displayName}</div>
                  {dept ? <div className="user-dept">{dept}</div> : null}
                </div>
              </div>
              <Button appearance="primary" size="small" icon={<AddRegular />} onClick={startNew}>
                New Proposal
              </Button>
              {teams && !teams.inTeams && (
                <Button appearance="subtle" size="small" icon={dark ? <WeatherSunnyRegular /> : <WeatherMoonRegular />} onClick={() => setTheme(dark ? "light" : "dark")} title="Toggle theme (browser preview only; Teams sets this itself)">
                  {dark ? "Light" : "Dark"}
                </Button>
              )}
            </div>
          </header>
        );
      })()}
      {error ? (
        <div className="page"><div className="err">Could not reach the API: {error}</div></div>
      ) : !meta ? (
        <div className="page"><Spinner label="Starting..." /></div>
      ) : proposalId ? (
        <Workspace meta={meta} proposalId={proposalId} initialTab={initialTab} onSwitch={close} onLogout={close} notify={notify} dark={dark} />
      ) : (
        <ProposalsPage meta={meta} initialMode={pickerMode} onOpen={open} notify={notify} />
      )}
    </FluentProvider>
  );
}
