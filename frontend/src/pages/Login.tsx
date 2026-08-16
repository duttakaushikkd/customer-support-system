import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";
import { saveSession } from "../auth";

export default function Login() {
  const [email, setEmail] = useState("customer@example.com");
  const [password, setPassword] = useState("customer123");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await login(email, password);
      saveSession({
        access_token: res.access_token,
        email: res.email,
        role: res.role,
        name: res.name,
      });
      navigate(res.role === "admin" ? "/admin" : "/chat");
    } catch {
      setError("Invalid credentials");
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <h1>Customer Support Agent</h1>
        <p className="muted">Local JWT auth (replaces Entra/MSAL).</p>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Sign in</button>
        <p className="hint">
          Demo users: customer@example.com / customer123 · admin@example.com / admin123
        </p>
      </form>
    </div>
  );
}
