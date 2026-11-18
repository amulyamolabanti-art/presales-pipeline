import { useState } from "react";
import { Button, Spinner } from "@fluentui/react-components";
import { ArrowClockwiseRegular, SendRegular } from "@fluentui/react-icons";
import { api, type ChatMessage } from "../api";

type Props = { proposalId: string; messages: ChatMessage[]; onMessages: (m: ChatMessage[]) => void; currentTab: string };

function inline(text: string) {
  // **bold** only, everything else stays plain text (his format_chat_reply does the same kind of light formatting)
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => (p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>));
}

/** Persistent chat: thread at the end of the page + input pinned to the bottom of the viewport (render_global_chat). */
export function ChatSection({ proposalId, messages, onMessages, currentTab }: Props) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setBusy(true);
    setError("");
    onMessages([...messages, { role: "user", content: q, created_at: "" }]);
    setInput("");
    try {
      const r = await api.chat(proposalId, q, currentTab);
      onMessages(r.messages);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <hr className="divider" style={{ marginTop: 24 }} />
      <div className="chat-panel">
        <div className="row">
          <h4 style={{ margin: 0 }}>Chat</h4>
          <span className="spacer" />
          {messages.length > 0 && (
            <Button appearance="subtle" size="small" icon={<ArrowClockwiseRegular />} onClick={async () => onMessages((await api.clearChat(proposalId)).messages)}>
              Clear
            </Button>
          )}
        </div>
        {messages.length === 0 ? (
          <div className="caption">
            Ask questions using analyzed text from Overview, Scope, Architecture, Estimates (Work Breakdown / Effort), and uploaded files.
            Chat stays available on every tab.
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i}>
              <div className="chat-role">{m.role === "user" ? "You" : "Assistant"}</div>
              <div className={"chat-bubble " + (m.role === "user" ? "chat-bubble-user" : "chat-bubble-assistant")}>{inline(m.content)}</div>
            </div>
          ))
        )}
        {busy && <div className="caption"><Spinner size="tiny" /> Thinking...</div>}
        {error && <div className="err">{error}</div>}
      </div>

      <div className="chat-dock">
        <div className="inner">
          <textarea
            rows={1}
            placeholder="Ask about this RFP..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
          />
          <Button appearance="primary" icon={<SendRegular />} onClick={() => void send()} disabled={!input.trim() || busy} style={{ background: "var(--apa-accent)" }} />
        </div>
      </div>
    </>
  );
}
