import { Link } from "react-router-dom";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-text-muted">
        <FileQuestion className="h-8 w-8" />
      </div>
      <h1 className="mt-5 font-display text-2xl font-semibold text-text">Page Not Found</h1>
      <p className="mt-2 max-w-sm text-sm text-text-muted">
        The page you're looking for doesn't exist or may have been moved.
      </p>
      <Link to="/" className="mt-6">
        <Button>Back to Dashboard</Button>
      </Link>
    </div>
  );
}
