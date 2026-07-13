"use client";

import { useTranslations } from "next-intl";
import { User, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScopeSelectorProps {
  value: "personal" | "organization";
  onChange: (scope: "personal" | "organization") => void;
  className?: string;
}

export default function ScopeSelector({
  value,
  onChange,
  className,
}: ScopeSelectorProps) {
  const t = useTranslations("common");

  const options = [
    { key: "personal" as const, icon: User, label: t("scopePersonal") },
    { key: "organization" as const, icon: Building2, label: t("scopeOrganization") },
  ];

  return (
    <div
      className={cn(
        "flex rounded-md border",
        className
      )}
    >
      {options.map((option) => {
        const Icon = option.icon;
        const isActive = value === option.key;

        return (
          <button
            key={option.key}
            onClick={() => onChange(option.key)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-brand-teal text-white"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
