import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api";
import { saveSession } from "../auth";

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  function storeAndGo(res: {
    access_token: string;
    role: "admin" | "customer";
    username: string;
    email?: string | null;
    name: string;
  }) {
    saveSession({
      access_token: res.access_token,
      username: res.username,
      email: res.email,
      role: res.role,
      name: res.name,
    });
    navigate(res.role === "admin" ? "/admin" : "/chat");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (mode === "register" && password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      const res =
        mode === "register"
          ? await register(username, email, password, displayName)
          : await login(username, password);
      storeAndGo(res);
    } catch (err) {
      setError((err as Error).message.replace(/^"|"$/g, "") || "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <h1>Customer Support Agent</h1>
        <p className="muted">Create an account, then sign in with that username and password.</p>
        <div className="mode-toggle">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            Sign in
          </button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            Register
          </button>
        </div>
        <label>
          Username
          <input
            value={username}
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            placeholder="your username"
          />
        </label>
        {mode === "register" && (
          <>
            <label>
              Email
              <input
                type="email"
                value={email}
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
              />
            </label>
            <label>
              Display name (optional)
              <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="How we should greet you" />
            </label>
          </>
        )}
        <label>
          Password
          <input
            type="password"
            value={password}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>
        {mode === "register" && (
          <label>
            Confirm password
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={6} />
          </label>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
        </button>
        <p className="hint">
          New users get a customer account. Built-in admin: username <code>admin</code> / password <code>admin123</code>.
        </p>
      </form>
    </div>
  );
}
