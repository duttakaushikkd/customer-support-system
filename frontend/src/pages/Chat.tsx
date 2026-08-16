import { FormEvent, useState } from "react";
import { ChatResponse, postChat } from "../api";
import { getSession } from "../auth";

type Bubble = { role: "user" | "agent"; text: string; ticket?: ChatResponse };

export default function Chat() {
  const session = getSession();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Bubble[]>([
    {
      role: "agent",
      text: "Hi — describe your issue and the agent pipeline will run Intake → Triage → RAG → Resolver → Critic → Manager.",
    },
  ]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || !session) return;
    const text = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await postChat(text, session.email, "chat");
      const reply = res.holding
        ? `We're holding ${res.ticket_number} for a human reviewer. You'll see it in the Admin Dashboard approval queue.`
        : res.resolution || "Resolved.";
      setMessages((m) => [...m, { role: "agent", text: reply, ticket: res }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "agent", text: `Request failed: ${(err as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="split">
      <section className="card chat-pane">
        <h2>Live Chat</h2>
        <div className="transcript">
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <p>{m.text}</p>
              {m.ticket && (
                <div className="meta">
                  <span className="badge">{m.ticket.ticket_number}</span>
                  <span className="badge">{m.ticket.ticket_type || m.ticket.category}</span>
                  <span className="badge">{Math.round(m.ticket.resolver_confidence * 100)}% confidence</span>
                  <span className="badge">{m.ticket.status}</span>
                </div>
              )}
            </div>
          ))}
        </div>
        <form className="composer" onSubmit={onSubmit}>
          <input
            value={input}
            disabled={busy}
            onChange={(e) => setInput(e.target.value)}
            placeholder={busy ? "Agents running…" : "Type your issue"}
          />
          <button disabled={busy || !input.trim()}>Send</button>
        </form>
      </section>
      <aside className="card trace">
        <h2>Reasoning trace</h2>
        {(() => {
          const last = [...messages].reverse().find((m) => m.ticket);
          if (!last?.ticket) return <p className="muted">Send a message to see the 7-agent loop.</p>;
          const t = last.ticket;
          return (
            <>
              <div className="loop-panel">
                <h3>Loop Engineering</h3>
                <p>Turn {String(t.loop_metadata.loop_turn)} / {String(t.loop_metadata.max_turns)}</p>
                <p>Human required: {t.requires_human ? "yes" : "no"}</p>
                <p>Flags: {(t.guardrail_flags || []).join(", ") || "none"}</p>
              </div>
              <ol>
                {t.reasoning_steps.map((s, i) => (
                  <li key={i}>
                    <strong>{s.agent}</strong>
                    <div>{s.summary}</div>
                    {s.detail && <small>{s.detail}</small>}
                  </li>
                ))}
              </ol>
            </>
          );
        })()}
      </aside>
    </div>
  );
}
