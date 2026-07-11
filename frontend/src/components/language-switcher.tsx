"use client";

import { useLocale } from "next-intl";

export function LanguageSwitcher() {
  const locale = useLocale();

  function switchLanguage(newLocale: string) {
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000; SameSite=Lax`;
    window.location.reload();
  }

  return (
    <div className="flex items-center gap-1 border rounded-md p-0.5">
      <button
        onClick={() => switchLanguage("en")}
        className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
          locale === "en"
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        EN
      </button>
      <button
        onClick={() => switchLanguage("ar")}
        className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
          locale === "ar"
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        AR
      </button>
    </div>
  );
}
