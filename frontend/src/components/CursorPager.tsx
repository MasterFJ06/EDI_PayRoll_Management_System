import { ArrowLeft, ArrowRight } from "lucide-react";

export function CursorPager({ page, limit, hasMore, onPrevious, onNext }: {
  page: number; limit: number; hasMore: boolean; onPrevious: () => void; onNext: () => void;
}) {
  return <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
    <span className="text-xs text-slate-500">Page {page} · {limit} per page</span>
    <div className="flex gap-2">
      <button type="button" disabled={page <= 1} onClick={onPrevious} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-2.5 text-xs font-medium text-slate-600 disabled:opacity-40"><ArrowLeft size={13} />Previous</button>
      <button type="button" disabled={!hasMore} onClick={onNext} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-2.5 text-xs font-medium text-slate-600 disabled:opacity-40">Next<ArrowRight size={13} /></button>
    </div>
  </div>;
}
