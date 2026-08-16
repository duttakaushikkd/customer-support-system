import { acquireTokenSilent } from "./auth";

const API = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (auth) {
    const token = acquireTokenSilent();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    let message = text || res.statusText;
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed?.detail === "string") message = parsed.detail;
    } catch {
      /* keep raw body */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export type ReasoningStep = {
  agent: string;
  summary: string;
  detail?: string | null;
  at: string;
};

export type ChatResponse = {
  ticket_id: string;
  ticket_number: string;
  status: string;
  channel: string;
  ticket_type?: string;
  category?: string;
  resolution?: string;
  requires_human: boolean;
  holding: boolean;
  resolver_confidence: number;
  reasoning_steps: ReasoningStep[];
  loop_metadata: Record<string, unknown>;
  guardrail_flags: string[];
  proposed_action?: string;
};

export type BackendTicket = {
  ticket_id: string;
  ticket_number: string;
  channel: string;
  customer_id: string;
  customer_email?: string;
  subject?: string;
  message: string;
  category?: string;
  ticket_type?: string;
  status: string;
  resolver_confidence: number;
  requires_human: boolean;
  proposed_action?: string;
  resolution?: string;
  created_at: string;
  updated_at: string;
  guardrail_flags?: string[];
};

export type Stats = {
  unique_users: number;
  total_tickets: number;
  resolved: number;
  escalated: number;
  not_resolved: number;
  pending_human_approval: number;
  resolution_rate_pct: number;
  by_channel: Record<string, number>;
};

export type Ticket = {
  id: string;
  backendTicketId: string;
  number: string;
  customer: string;
  channel: string;
  subject: string;
  status: string;
  priority: "low" | "medium" | "high";
  createdRelative: string;
  createdAt: string;
  confidence: number;
  requiresHuman: boolean;
  resolution?: string;
};

export async function login(username: string, password: string) {
  return request<{
    access_token: string;
    role: "admin" | "customer";
    username: string;
    email?: string | null;
    name: string;
  }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false);
}

export async function register(username: string, password: string, display_name?: string) {
  return request<{
    access_token: string;
    role: "admin" | "customer";
    username: string;
    email?: string | null;
    name: string;
  }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({ username, password, display_name: display_name || undefined }),
    },
    false
  );
}

export async function postChat(message: string, user_id: string, channel = "chat") {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, user_id, channel }),
  });
}

export async function getTickets(limit = 200) {
  return request<BackendTicket[]>(`/tickets?limit=${limit}`);
}

export async function getStats() {
  return request<Stats>("/tickets/stats");
}

export async function postHumanDecision(ticketId: string, decision: "approved" | "rejected") {
  return request<ChatResponse>(`/tickets/${ticketId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const delta = Math.max(0, Date.now() - then);
  const mins = Math.floor(delta / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function priorityFrom(ticket: BackendTicket): Ticket["priority"] {
  if (ticket.proposed_action === "reset_2fa" || ticket.proposed_action === "escalate_security") return "high";
  if (ticket.requires_human || ticket.status === "pending_human_approval") return "high";
  if ((ticket.resolver_confidence || 0) < 0.5) return "medium";
  return "low";
}

export function mapBackendTicket(doc: BackendTicket): Ticket {
  return {
    id: doc.ticket_number,
    backendTicketId: doc.ticket_id,
    number: doc.ticket_number,
    customer: doc.customer_email || doc.customer_id,
    channel: doc.channel,
    subject: doc.subject || doc.message.slice(0, 80),
    status: doc.status,
    priority: priorityFrom(doc),
    createdRelative: relativeTime(doc.created_at || doc.updated_at),
    createdAt: doc.created_at,
    confidence: doc.resolver_confidence,
    requiresHuman: doc.requires_human,
    resolution: doc.resolution,
  };
}
