import { useEffect, useState } from "react";
import { getTickets, mapBackendTicket, Ticket } from "../api";

export default function Portal() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getTickets(50)
      .then((docs) => setTickets(docs.map(mapBackendTicket)))
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div className="card">
      <h2>Customer Portal</h2>
      <p className="muted">Your tickets from live chat and the portal.</p>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Ticket</th>
            <th>Channel</th>
            <th>Subject</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((t) => (
            <tr key={t.backendTicketId}>
              <td>{t.number}</td>
              <td>{t.channel}</td>
              <td>{t.subject}</td>
              <td>{t.status}</td>
              <td>{t.createdRelative}</td>
            </tr>
          ))}
          {tickets.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No tickets yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
