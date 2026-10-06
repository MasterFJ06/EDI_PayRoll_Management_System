import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pagination } from "@/components/common/Pagination";
import { LoadingState } from "@/components/common/LoadingState";
import { EmptyState } from "@/components/common/EmptyState";
import { cn } from "@/utils/cn";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  pageSize?: number;
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  columns, data, rowKey, loading, emptyTitle = "No records found", emptyDescription,
  pageSize = 8, onRowClick,
}: DataTableProps<T>) {
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return data;
    const copy = [...data];
    copy.sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [data, sortKey, sortDir, columns]);

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, page, pageSize]);

  function toggleSort(col: Column<T>) {
    if (!col.sortValue) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col.key);
      setSortDir("asc");
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-slate-50/70">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn("px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-muted", col.headerClassName)}
                >
                  {col.sortValue ? (
                    <button
                      onClick={() => toggleSort(col)}
                      className="inline-flex items-center gap-1 hover:text-text"
                    >
                      {col.header}
                      {sortKey === col.key ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!loading && paged.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={() => onRowClick?.(row)}
                className={cn("border-b border-border last:border-0 hover:bg-slate-50/70 transition-colors", onRowClick && "cursor-pointer")}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-4 py-3 align-middle text-text", col.className)}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {loading && <LoadingState label="Loading records..." />}
      {!loading && data.length === 0 && <EmptyState title={emptyTitle} description={emptyDescription} />}
      {!loading && data.length > 0 && (
        <Pagination page={page} pageSize={pageSize} total={data.length} onPageChange={setPage} />
      )}
    </Card>
  );
}
