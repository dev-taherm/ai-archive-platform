import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-screen gap-4">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <Link
        href="/dashboard"
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}
