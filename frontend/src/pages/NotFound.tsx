import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";

export function NotFound() {
  return (
    <div className="relative z-10 flex min-h-full flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="font-mono text-xs text-[var(--color-ink-subtle)]">404</p>
      <h1 className="text-lg font-semibold">This page does not exist</h1>
      <Link to="/dashboard">
        <Button size="sm">Back to dashboard</Button>
      </Link>
    </div>
  );
}
