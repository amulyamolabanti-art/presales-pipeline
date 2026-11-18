import type { Bundle, Meta } from "../api";

export type TabProps = {
  meta: Meta;
  bundle: Bundle;
  setBundle: (b: Bundle | ((prev: Bundle) => Bundle)) => void;
  analyzing: Set<string>;
  runAnalyze: (fields: string[], label: string) => Promise<void>;
  notify: (text: string, kind?: "ok" | "err") => void;
};
