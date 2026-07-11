import { BasirahLogo } from "@/components/ui/basirah-logo";
import { useTranslations } from "next-intl";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("auth");
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-background to-brand-teal/5 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4">
            <BasirahLogo size={48} variant="full" />
          </div>
          <p className="text-sm text-muted-foreground max-w-xs">
            {t("tagline")}
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
