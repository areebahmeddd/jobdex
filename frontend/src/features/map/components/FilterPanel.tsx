import {
  FILTER_GROUPS,
  POSTED_OPTIONS,
  labelFor,
  type FilterGroup,
  type FilterKey,
} from "@/lib/filters";
import type { JobFacets } from "@/types";
import { Check, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  selections: Record<FilterKey, string[]>;
  posted: number | null;
  facets: JobFacets | null;
  facetsLoading: boolean;
  activeCount: number;
  onToggle: (key: FilterKey, value: string) => void;
  onClearGroup: (key: FilterKey) => void;
  onPostedChange: (days: number | null) => void;
  onClearAll: () => void;
  onClose: () => void;
};

type Option = { value: string; label: string; count: number | null };

type Section = {
  id: string;
  title: string;
  summary: string;
  selectedCount: number;
  single: boolean;
  options: Option[];
  isSelected: (value: string) => boolean;
  onPick: (value: string) => void;
  onClear: () => void;
};

const POSTED_SECTION_ID = "posted";

function optionsFor(
  group: FilterGroup,
  facets: JobFacets | null,
  selected: string[],
): Option[] {
  const counts = new Map(
    (facets?.[group.facet] ?? []).map((b) => [b.value, b.count]),
  );
  const values = facets
    ? [...new Set([...counts.keys(), ...selected])]
    : Object.keys(group.labels);

  const options = values.map((value) => ({
    value,
    label: labelFor(group.key, value),
    count: facets ? (counts.get(value) ?? 0) : null,
  }));

  if (group.order) {
    const rank = new Map(group.order.map((v, i) => [v, i]));
    return options.sort(
      (a, b) =>
        (rank.get(a.value) ?? 99) - (rank.get(b.value) ?? 99) ||
        a.label.localeCompare(b.label),
    );
  }
  return options.sort(
    (a, b) => (b.count ?? 0) - (a.count ?? 0) || a.label.localeCompare(b.label),
  );
}

function summarize(selected: string[], key: FilterKey): string {
  if (selected.length === 0) return "Any";
  if (selected.length === 1) return labelFor(key, selected[0]);
  return `${selected.length} selected`;
}

function OptionRow({
  label,
  count,
  checked,
  single,
  onClick,
}: {
  label: string;
  count: number | null;
  checked: boolean;
  single: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role={single ? "radio" : "checkbox"}
      aria-checked={checked}
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
    >
      <span
        aria-hidden="true"
        className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center border transition-colors ${single ? "rounded-full" : "rounded"} ${
          checked ? "border-black bg-black" : "border-black/20 bg-white"
        }`}
      >
        {checked &&
          (single ? (
            <span className="h-1.5 w-1.5 rounded-full bg-white" />
          ) : (
            <Check className="h-2.5 w-2.5 text-white" />
          ))}
      </span>
      <span className="flex-1 truncate text-xs text-gray-700">{label}</span>
      {count !== null && (
        <span className="shrink-0 text-[10px] text-gray-500 tabular-nums">
          {count.toLocaleString()}
        </span>
      )}
    </button>
  );
}

export function FilterPanel({
  selections,
  posted,
  facets,
  facetsLoading,
  activeCount,
  onToggle,
  onClearGroup,
  onPostedChange,
  onClearAll,
  onClose,
}: Props) {
  const [openSectionId, setOpenSectionId] = useState<string | null>(null);
  const backRef = useRef<HTMLButtonElement>(null);
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const lastOpenedRef = useRef<string | null>(null);

  const sections: Section[] = useMemo(() => {
    const postedSection: Section = {
      id: POSTED_SECTION_ID,
      title: "Date posted",
      summary:
        POSTED_OPTIONS.find((o) => o.value === posted)?.label ?? "Any time",
      selectedCount: posted ? 1 : 0,
      single: true,
      options: POSTED_OPTIONS.map((o) => ({
        value: o.value === null ? "" : String(o.value),
        label: o.label,
        count: null,
      })),
      isSelected: (value) =>
        posted === null ? value === "" : value === String(posted),
      onPick: (value) => onPostedChange(value === "" ? null : Number(value)),
      onClear: () => onPostedChange(null),
    };

    return [
      postedSection,
      ...FILTER_GROUPS.map((group): Section => {
        const selected = selections[group.key];
        return {
          id: group.key,
          title: group.title,
          summary: summarize(selected, group.key),
          selectedCount: selected.length,
          single: false,
          options: optionsFor(group, facets, selected),
          isSelected: (value) => selected.includes(value),
          onPick: (value) => onToggle(group.key, value),
          onClear: () => onClearGroup(group.key),
        };
      }),
    ];
  }, [selections, posted, facets, onToggle, onClearGroup, onPostedChange]);

  const openSection = sections.find((s) => s.id === openSectionId) ?? null;

  useEffect(() => {
    if (openSectionId) backRef.current?.focus();
    else if (lastOpenedRef.current)
      rowRefs.current[lastOpenedRef.current]?.focus();
  }, [openSectionId]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (openSectionId) setOpenSectionId(null);
      else onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [openSectionId, onClose]);

  return (
    <div
      role="dialog"
      aria-label="Filter jobs"
      className="w-full overflow-hidden rounded-2xl border border-white/20 bg-white/85 shadow-lg shadow-black/10 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between gap-2 border-b border-black/8 px-2 py-2">
        {openSection ? (
          <button
            ref={backRef}
            type="button"
            onClick={() => setOpenSectionId(null)}
            aria-label={`Back to all filters, from ${openSection.title}`}
            className="flex min-w-0 items-center gap-1 rounded-lg px-1 py-0.5 text-[11px] font-medium text-gray-700 transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
          >
            <ChevronLeft className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{openSection.title}</span>
          </button>
        ) : (
          <span className="px-1 text-[10px] font-medium tracking-widest text-gray-500 uppercase">
            Filters
          </span>
        )}
        <span className="flex shrink-0 items-center gap-1.5">
          {facetsLoading && (
            <Loader2
              className="h-3 w-3 animate-spin text-gray-300"
              aria-hidden="true"
            />
          )}
          {facets && (
            <span
              aria-live="polite"
              className="text-[10px] text-gray-500 tabular-nums"
            >
              {facets.total.toLocaleString()} jobs
            </span>
          )}
        </span>
      </div>

      <div className="no-scrollbar max-h-[min(50vh,19rem)] min-h-44 overflow-y-auto p-1.5">
        {openSection ? (
          openSection.options.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-4 py-6 text-center">
              <p className="text-xs text-gray-500">
                No {openSection.title.toLowerCase()} options match your other
                filters.
              </p>
              <button
                type="button"
                onClick={onClearAll}
                className="text-[11px] font-medium text-gray-700 underline underline-offset-2 transition-colors hover:text-black"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <div role={openSection.single ? "radiogroup" : "group"}>
              {openSection.options.map((opt) => (
                <OptionRow
                  key={opt.value}
                  label={opt.label}
                  count={opt.count}
                  single={openSection.single}
                  checked={openSection.isSelected(opt.value)}
                  onClick={() => openSection.onPick(opt.value)}
                />
              ))}
            </div>
          )
        ) : (
          sections.map((section) => (
            <button
              key={section.id}
              ref={(el) => {
                rowRefs.current[section.id] = el;
              }}
              type="button"
              onClick={() => {
                lastOpenedRef.current = section.id;
                setOpenSectionId(section.id);
              }}
              aria-label={`${section.title}: ${section.summary}`}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
            >
              <span className="shrink-0 text-xs text-gray-700">
                {section.title}
              </span>
              <span
                className={`ml-auto min-w-0 truncate text-[11px] ${
                  section.selectedCount > 0
                    ? "font-medium text-gray-900"
                    : "text-gray-500"
                }`}
              >
                {section.summary}
              </span>
              <ChevronRight
                className="h-3 w-3 shrink-0 text-gray-300"
                aria-hidden="true"
              />
            </button>
          ))
        )}
      </div>

      <div className="flex items-center justify-between border-t border-black/8 bg-white/60 px-3 py-2">
        {openSection ? (
          <button
            type="button"
            onClick={openSection.onClear}
            disabled={openSection.selectedCount === 0}
            className="text-[11px] text-gray-500 transition-colors hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear {openSection.title.toLowerCase()}
          </button>
        ) : (
          <button
            type="button"
            onClick={onClearAll}
            disabled={activeCount === 0}
            className="text-[11px] text-gray-500 transition-colors hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear all
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className="rounded-full bg-black px-3 py-1.5 text-[11px] font-medium text-white transition-colors hover:bg-gray-800"
        >
          Done
        </button>
      </div>
    </div>
  );
}
