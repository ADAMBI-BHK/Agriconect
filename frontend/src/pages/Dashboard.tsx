import { NavLink } from "react-router-dom";
import { useAuth } from "../App";
import Graduate from "./dash/Graduate";
import Company from "./dash/Company";
import Institution from "./dash/Institution";
import Admin from "./dash/Admin";

export function Shell({ title, items, children }: { title: string; items: [string, string, boolean?][]; children: any }) {
  return (<div className="dash">
    <aside className="side"><b className="side-t">{title}</b>
      {items.map(([to, label, end]) => <NavLink key={to} to={"/tableau-de-bord" + to} end={end}>{label}</NavLink>)}</aside>
    <section className="dash-main">{children}</section></div>);
}

export default function Dashboard() {
  const { user } = useAuth();
  if (user!.role === "graduate") return <Graduate />;
  if (user!.role === "company") return <Company />;
  if (user!.role === "institution") return <Institution />;
  return <Admin />;
}
