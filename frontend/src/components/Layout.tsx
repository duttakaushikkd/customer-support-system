import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearSession, getSession } from "../auth";

export default function Layout() {
  const session = getSession();
  const navigate = useNavigate();
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">Support Agent</div>
        <nav>
          <NavLink to="/chat">Live Chat</NavLink>
          <NavLink to="/portal">Customer Portal</NavLink>
          {session?.role === "admin" && <NavLink to="/admin">Admin Dashboard</NavLink>}
        </nav>
        <div className="session">
          <span>{session?.name || session?.username}</span>
          <button
            className="linkish"
            onClick={() => {
              clearSession();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
