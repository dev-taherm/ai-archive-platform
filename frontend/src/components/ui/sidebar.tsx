"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  FolderOpen,
  Search,
  Settings,
  ChevronLeft,
  MessageSquare,
  BarChart3,
  GitBranch,
  Bot,
  Brain,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import OrgSwitcher from "@/components/features/organization/org-switcher";
import { BasirahLogo } from "@/components/ui/basirah-logo";

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const t = useTranslations("sidebar");

  const navItems = [
    { label: t("dashboard"), href: "/dashboard", icon: LayoutDashboard },
    { label: t("files"), href: "/files", icon: FolderOpen },
    { label: t("documents"), href: "/documents", icon: FileText },
    { label: t("aiWorkspace"), href: "/ai-workspace", icon: Brain },
    { label: t("devices"), href: "/agents", icon: Bot },
    { label: t("search"), href: "/search", icon: Search },
    { label: t("workflows"), href: "/workflows", icon: GitBranch },
    { label: t("reports"), href: "/reports", icon: BarChart3 },
    { label: t("chat"), href: "/chat", icon: MessageSquare },
    { label: t("settings"), href: "/settings", icon: Settings },
  ];

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-300",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex h-14 items-center justify-between border-b px-4">
          {sidebarOpen && (
            <Link href="/dashboard" className="flex items-center gap-2">
              <BasirahLogo size={28} />
              <span className="font-bold text-lg">{t("basirah")}</span>
            </Link>
          )}
          {!sidebarOpen && (
            <Link href="/dashboard" className="mx-auto">
              <BasirahLogo size={24} />
            </Link>
          )}
          <button
            onClick={toggleSidebar}
            className="rounded-md p-1 hover:bg-muted"
          >
            <ChevronLeft
              className={cn(
                "h-4 w-4 transition-transform",
                !sidebarOpen && "rotate-180"
              )}
            />
          </button>
        </div>

        {sidebarOpen && (
          <div className="border-b px-2 py-2">
            <OrgSwitcher />
          </div>
        )}

        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-teal/10 text-brand-teal"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  isActive && "border-l-2 border-brand-teal"
                )}
                title={!sidebarOpen ? item.label : undefined}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}