import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function ErrorState({ message = "Something went wrong.", onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-50 text-danger">
        <AlertCircle className="h-5 w-5" />
      </div>
      <div>
        <p className="text-sm font-medium text-text">Unable to load this page</p>
        <p className="mt-1 text-sm text-text-muted max-w-sm">{message}</p>
      </div>
      {onRetry && <Button size="sm" variant="outline" onClick={onRetry} className="mt-1">Try again</Button>}
    </div>
  );
}
