import Link from "next/link";
import { BasirahLogo } from "@/components/ui/basirah-logo";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-screen gap-6 bg-gradient-to-br from-background via-background to-brand-teal/5">
      <BasirahLogo size={48} />
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <Link
        href="/dashboard"
        className="px-4 py-2 bg-gradient-to-r from-brand-teal to-brand-cyan text-white rounded-md text-sm hover:opacity-90 transition-opacity"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}
