import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function Forbidden() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-danger-50 text-danger">
        <ShieldAlert className="h-8 w-8" />
      </div>
      <h1 className="mt-5 font-display text-2xl font-semibold text-text">Access Denied</h1>
      <p className="mt-2 max-w-sm text-sm text-text-muted">
        You do not have permission to view this page. If you believe this is a mistake,
        contact your System Administrator.
      </p>
      <Link to="/" className="mt-6">
        <Button>Back to Dashboard</Button>
      </Link>
    </div>
  );
}
