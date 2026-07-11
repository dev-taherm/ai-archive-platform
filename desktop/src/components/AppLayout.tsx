import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../stores/auth-store";
import { Button } from "./ui/button";
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  Trash2,
  LogOut,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, labelKey: "nav.dashboard" },
  { to: "/folders", icon: FolderOpen, labelKey: "nav.folders" },
  { to: "/trash", icon: Trash2, labelKey: "nav.trash" },
  { to: "/settings", icon: Settings, labelKey: "nav.settings" },
];

export default function AppLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const isRtl = i18n.language === "ar";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleToggleLanguage = () => {
    i18n.changeLanguage(i18n.language === "ar" ? "en" : "ar");
  };

  const displayName = user
    ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email
    : null;

  return (
    <div className={cn("flex h-screen", isRtl && "flex-row-reverse")}>
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r bg-background">
        {/* Logo */}
        <div className="flex h-12 items-center border-b px-4">
          <span className="text-sm font-semibold">Basirah</span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>

        {/* Bottom actions */}
        <div className="border-t p-2 space-y-1">
          {displayName && (
            <div className="flex items-center gap-2 rounded-md px-3 py-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <User className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium leading-tight">{displayName}</p>
                {user?.email && user.email !== displayName && (
                  <p className="truncate text-xs text-muted-foreground leading-tight">{user.email}</p>
                )}
              </div>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={handleToggleLanguage}
          >
            {i18n.language === "ar" ? "EN" : "عربي"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4 mr-2" />
            {t("common.logout")}
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
