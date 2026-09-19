import { Dialog } from "./Dialog";
import { Button } from "./Button";
import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
}

export function ConfirmDialog({ open, onClose, onConfirm, title, description, confirmLabel = "Confirm", danger, loading }: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
        </>
      }
    >
      <div className="flex gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${danger ? "bg-danger-50" : "bg-warning-50"}`}>
          <AlertTriangle className={`h-[18px] w-[18px] ${danger ? "text-danger" : "text-warning"}`} />
        </div>
        <p className="text-sm text-text-muted pt-1.5">{description}</p>
      </div>
    </Dialog>
  );
}
