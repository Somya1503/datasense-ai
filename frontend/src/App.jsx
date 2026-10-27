import { useEffect, useState } from "react";
import LandingPage from "./components/LandingPage";
import Workspace from "./Workspace";

export default function App() {
  useEffect(() => {
    if (window.location.pathname !== "/" && window.location.pathname !== "/workspace") {
      window.history.replaceState({}, "", "/");
    }
  }, []);

  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const openWorkspace = () => {
    window.history.pushState({}, "", "/workspace");
    setPathname("/workspace");
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  return pathname === "/workspace" ? <Workspace /> : <LandingPage onOpenWorkspace={openWorkspace} />;
}
