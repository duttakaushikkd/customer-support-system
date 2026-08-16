import { useCallback, useEffect, useState } from "react";
import { getStats, getTickets, mapBackendTicket, postHumanDecision, Stats, Ticket } from "../api";

export default function Admin() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [live, setLive] = useState(true);
  const [from, setFrom] = useState("");
  const [error, setError] = useState("");

  const sync = useCallback(async () => {
    try {
      const [s, docs] = await Promise.all([getStats(), getTickets(200)]);
      setStats(s);
      setTickets(docs.map(mapBackendTicket));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    sync();
  }, [sync]);

  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(sync, 15000);
    return () => window.clearInterval(id);
  }, [live, sync]);

  async function decide(ticket: Ticket, decision: "approved" | "rejected") {
    await postHumanDecision(ticket.backendTicketId, decision);
    await sync();
  }

  const filtered = tickets.filter((t) => {
    if (!from) return true;
    return new Date(t.createdAt).getTime() >= new Date(from).getTime();
  });
  const queue = filtered.filter((t) => t.status === "pending_human_approval");

  return (
    <div className="stack">
      <div className="row">
        <h2>Admin Dashboard</h2>
        <button onClick={() => setLive((v) => !v)}>{live ? "Pause live" : "Resume live"}</button>
      </div>
      {error && <p className="error">{error}</p>}
      <section className="card">
        <h3>Live Backend Usage</h3>
        <div className="stats">
          <Stat label="Unique users" value={stats?.unique_users} />
          <Stat label="Resolved" value={stats?.resolved} />
          <Stat label="Escalated" value={stats?.escalated} />
          <Stat label="Not resolved" value={stats?.not_resolved} />
          <Stat label="Resolution rate" value={stats ? `${stats.resolution_rate_pct}%` : "—"} />
        </div>
        <p className="muted">
          By channel:{" "}
          {stats
            ? Object.entries(stats.by_channel)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ") || "none"
            : "loading"}
        </p>
      </section>

      <section className="card">
        <div className="row">
          <h3>Tickets</h3>
          <label>
            From date
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
        </div>
        <table>
          <thead>
            <tr>
              <th>Number</th>
              <th>Customer</th>
              <th>Channel</th>
              <th>Priority</th>
              <th>Status</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.backendTicketId}>
                <td>{t.number}</td>
                <td>{t.customer}</td>
                <td>{t.channel}</td>
                <td>{t.priority}</td>
                <td>{t.status}</td>
                <td>{t.createdRelative}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>Human Safeguard Queue</h3>
        {queue.length === 0 && <p className="muted">No tickets waiting for approval.</p>}
        {queue.map((t) => (
          <div key={t.backendTicketId} className="queue-item">
            <div>
              <strong>{t.number}</strong> · {t.customer} · {t.subject}
            </div>
            <div className="row">
              <button onClick={() => decide(t, "approved")}>Approve</button>
              <button className="danger" onClick={() => decide(t, "rejected")}>
                Reject & Escalate
              </button>
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <h3>Analytics</h3>
        <div className="bars">
          {(["resolved", "escalated", "not_resolved"] as const).map((key) => {
            const val = stats?.[key] ?? 0;
            const max = Math.max(stats?.total_tickets || 1, 1);
            return (
              <div key={key} className="bar-row">
                <span>{key.replace("_", " ")}</span>
                <div className="bar">
                  <i style={{ width: `${(100 * val) / max}%` }} />
                </div>
                <span>{val}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string | undefined }) {
  return (
    <div className="stat">
      <div className="stat-value">{value ?? "—"}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
