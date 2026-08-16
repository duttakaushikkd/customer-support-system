import { Navigate, Route, Routes } from "react-router-dom";
import { getSession } from "./auth";
import Admin from "./pages/Admin";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Portal from "./pages/Portal";
import Layout from "./components/Layout";

function RequireAuth({ children, admin }: { children: JSX.Element; admin?: boolean }) {
  const session = getSession();
  if (!session) return <Navigate to="/login" replace />;
  if (admin && session.role !== "admin") return <Navigate to="/chat" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/chat" element={<Chat />} />
        <Route path="/portal" element={<Portal />} />
        <Route
          path="/admin"
          element={
            <RequireAuth admin>
              <Admin />
            </RequireAuth>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
