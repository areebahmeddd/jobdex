import type { PanelMode } from "@/features/map/hooks/useJobFilters";
import { SORT_OPTIONS, type SortValue } from "@/lib/filters";
import { ArrowUpDown, Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type Props = {
  mode: PanelMode;
  onModeChange: (mode: PanelMode) => void;
  total: number | null;
  loading: boolean;
  sort: SortValue;
  onSortChange: (sort: SortValue) => void;
  hasQuery: boolean;
};

function countLabel(mode: PanelMode, total: number | null): string {
  if (total === null) return mode === "jobs" ? "Jobs" : "Companies";
  const noun = mode === "jobs" ? "job" : "company";
  const plural = mode === "jobs" ? "jobs" : "companies";
  return `${total.toLocaleString()} ${total === 1 ? noun : plural}`;
}

function SortMenu({
  sort,
  onSortChange,
  hasQuery,
}: Pick<Props, "sort" | "onSortChange" | "hasQuery">) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const current = SORT_OPTIONS.find((o) => o.value === sort) ?? SORT_OPTIONS[0];

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`Sort by ${current.label}`}
        className="flex items-center gap-1 rounded-full px-1.5 py-1 text-[11px] text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900"
      >
        <ArrowUpDown className="h-2.5 w-2.5" aria-hidden="true" />
        {current.label}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute top-full right-0 z-10 mt-1 w-40 overflow-hidden rounded-xl border border-black/10 bg-white/95 shadow-lg shadow-black/10 backdrop-blur-xl"
        >
          {SORT_OPTIONS.map((opt) => {
            const disabled = opt.needsQuery && !hasQuery;
            return (
              <button
                key={opt.value}
                type="button"
                role="menuitemradio"
                aria-checked={sort === opt.value}
                disabled={disabled}
                title={
                  disabled
                    ? "Type a search term to sort by relevance"
                    : undefined
                }
                onClick={() => {
                  onSortChange(opt.value);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[11px] text-gray-700 transition-colors hover:bg-black/5 disabled:cursor-not-allowed disabled:text-gray-300 disabled:hover:bg-transparent"
              >
                <Check
                  className={`h-2.5 w-2.5 shrink-0 ${sort === opt.value ? "opacity-100" : "opacity-0"}`}
                  aria-hidden="true"
                />
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ResultsToolbar({
  mode,
  onModeChange,
  total,
  loading,
  sort,
  onSortChange,
  hasQuery,
}: Props) {
  return (
    <div className="flex shrink-0 flex-col gap-1.5 border-b border-black/8 px-3 py-2">
      <div
        role="tablist"
        aria-label="Result type"
        className="flex items-center gap-0.5 rounded-full bg-black/5 p-0.5"
      >
        {(["jobs", "companies"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={mode === value}
            onClick={() => onModeChange(value)}
            className={`flex-1 rounded-full py-1 text-[11px] font-medium capitalize transition-colors ${
              mode === value
                ? "bg-white text-gray-900 shadow-sm shadow-black/5"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {value}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between gap-2">
        <span
          aria-live="polite"
          className="truncate text-[11px] font-medium text-gray-600"
        >
          {loading ? "Searching…" : countLabel(mode, total)}
        </span>
        {mode === "jobs" && (
          <SortMenu
            sort={sort}
            onSortChange={onSortChange}
            hasQuery={hasQuery}
          />
        )}
      </div>
    </div>
  );
}
