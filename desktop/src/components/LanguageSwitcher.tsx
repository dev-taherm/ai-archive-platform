import { useTranslation } from "react-i18next";
import { Button } from "./ui/button";

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const isArabic = i18n.language === "ar";

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => i18n.changeLanguage(isArabic ? "en" : "ar")}
    >
      {isArabic ? "EN" : "عربي"}
    </Button>
  );
}
