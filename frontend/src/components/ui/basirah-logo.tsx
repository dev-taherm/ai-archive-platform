"use client";

import { cn } from "@/lib/utils";

interface BasirahLogoProps {
  size?: number;
  className?: string;
  variant?: "icon" | "full";
}

export function BasirahLogo({
  size = 32,
  className,
  variant = "icon",
}: BasirahLogoProps) {
  const iconSize = variant === "full" ? size * 0.6 : size;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-3",
        variant === "full" && "select-none",
        className
      )}
    >
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        {/* Document body */}
        <rect
          x="3"
          y="2"
          width="26"
          height="28"
          rx="3"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        {/* Folded corner */}
        <path
          d="M21 2v4a2 2 0 0 0 2 2h4"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Content lines on document */}
        <line
          x1="9"
          y1="12"
          x2="19"
          y2="12"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.3"
        />
        <line
          x1="9"
          y1="16"
          x2="23"
          y2="16"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.3"
        />
        <line
          x1="9"
          y1="20"
          x2="17"
          y2="20"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.3"
        />
        {/* Knowledge graph nodes */}
        <circle cx="12" cy="14" r="2" fill="currentColor" opacity="0.8" />
        <circle cx="20" cy="10" r="2" fill="currentColor" opacity="0.8" />
        <circle cx="20" cy="18" r="2" fill="currentColor" opacity="0.8" />
        <circle cx="16" cy="14" r="1.5" fill="currentColor" opacity="0.5" />
        {/* Connections between nodes */}
        <line x1="12" y1="14" x2="20" y2="10" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="12" y1="14" x2="20" y2="18" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="20" y1="10" x2="20" y2="18" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="12" y1="14" x2="16" y2="14" stroke="currentColor" strokeWidth="1" opacity="0.4" />
      </svg>
      {variant === "full" && (
        <div className="flex flex-col leading-tight">
          <span className="text-lg font-bold tracking-tight">بصيرة</span>
          <span className="text-xs font-medium text-muted-foreground tracking-wide">
            Basirah
          </span>
        </div>
      )}
    </div>
  );
}
