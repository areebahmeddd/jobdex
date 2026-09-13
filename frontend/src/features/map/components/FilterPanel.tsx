import {
  FILTER_GROUPS,
  POSTED_OPTIONS,
  countryName,
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
  city: string | null;
  country: string | null;
  facets: JobFacets | null;
  facetsLoading: boolean;
  activeCount: number;
  onToggle: (key: FilterKey, value: string) => void;
  onClearGroup: (key: FilterKey) => void;
  onPostedChange: (days: number | null) => void;
  onPickCity: (city: string) => void;
  onPickCountry: (code: string) => void;
  onClearLocation: () => void;
  onClearAll: () => void;
  onClose: () => void;
};

type Option = {
  value: string;
  label: string;
  count: number | null;
  drill?: string;
};

type Screen = {
  id: string;
  title: string;
  single: boolean;
  selectedCount: number;
  options: Option[];
  isSelected: (value: string) => boolean;
  onPick: (value: string) => void;
  onClear: () => void;
  clearLabel: string;
};

type RootRow = { id: string; title: string; summary: string; active: boolean };

const POSTED_ID = "posted";
const LOCATION_ID = "location";
const ANYWHERE = "";

function optionsFor(
  group: FilterGroup,
  facets: JobFacets | null,
  selected: string[],
): Option[] {
  const counts = new Map(
    (facets?.[group.facet] ?? []).map((bucket) => [bucket.value, bucket.count]),
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

function byLabel(a: Option, b: Option) {
  return a.label.localeCompare(b.label);
}

function OptionRow({
  option,
  checked,
  single,
  onClick,
}: {
  option: Option;
  checked: boolean;
  single: boolean;
  onClick: () => void;
}) {
  const drills = Boolean(option.drill);
  return (
    <button
      type="button"
      role={drills ? undefined : single ? "radio" : "checkbox"}
      aria-checked={drills ? undefined : checked}
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
    >
      {!drills && (
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
      )}
      <span
        className={`flex-1 truncate text-xs ${checked && drills ? "font-medium text-gray-900" : "text-gray-700"}`}
      >
        {option.label}
      </span>
      {option.count !== null && (
        <span className="shrink-0 text-[10px] text-gray-500 tabular-nums">
          {option.count.toLocaleString()}
        </span>
      )}
      {drills && (
        <ChevronRight
          className="h-3 w-3 shrink-0 text-gray-300"
          aria-hidden="true"
        />
      )}
    </button>
  );
}

export function FilterPanel({
  selections,
  posted,
  city,
  country,
  facets,
  facetsLoading,
  activeCount,
  onToggle,
  onClearGroup,
  onPostedChange,
  onPickCity,
  onPickCountry,
  onClearLocation,
  onClearAll,
  onClose,
}: Props) {
  const [path, setPath] = useState<string[]>([]);
  const backRef = useRef<HTMLButtonElement>(null);
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const lastOpenedRef = useRef<string | null>(null);

  const cityParent = useMemo(
    () =>
      city
        ? (facets?.city.find((bucket) => bucket.value === city)?.parent ?? null)
        : null,
    [city, facets],
  );
  const selectedCountry = country ?? cityParent;

  const locationSummary = city
    ? cityParent
      ? `${city}, ${countryName(cityParent)}`
      : city
    : country
      ? countryName(country)
      : "Anywhere";

  const rootRows: RootRow[] = useMemo(
    () => [
      {
        id: LOCATION_ID,
        title: "Location",
        summary: locationSummary,
        active: Boolean(city || country),
      },
      {
        id: POSTED_ID,
        title: "Date posted",
        summary:
          POSTED_OPTIONS.find((option) => option.value === posted)?.label ??
          "Any time",
        active: posted !== null,
      },
      ...FILTER_GROUPS.map((group) => ({
        id: group.key,
        title: group.title,
        summary: summarize(selections[group.key], group.key),
        active: selections[group.key].length > 0,
      })),
    ],
    [locationSummary, city, country, posted, selections],
  );

  const screen: Screen | null = useMemo(() => {
    const [head, sub] = path;
    if (!head) return null;

    if (head === LOCATION_ID && !sub) {
      const countries = (facets?.country_code ?? [])
        .map((bucket) => ({
          value: bucket.value,
          label: countryName(bucket.value),
          count: bucket.count,
          drill: bucket.value,
        }))
        .sort(byLabel);
      return {
        id: LOCATION_ID,
        title: "Location",
        single: true,
        selectedCount: city || country ? 1 : 0,
        options: [
          { value: ANYWHERE, label: "Anywhere", count: null },
          ...countries,
        ],
        isSelected: (value) =>
          value === ANYWHERE ? !city && !country : selectedCountry === value,
        onPick: (value) => {
          if (value === ANYWHERE) onClearLocation();
        },
        onClear: onClearLocation,
        clearLabel: "Clear location",
      };
    }

    if (head === LOCATION_ID && sub) {
      const cities = (facets?.city ?? [])
        .filter((bucket) => bucket.parent === sub)
        .map((bucket) => ({
          value: bucket.value,
          label: bucket.value,
          count: bucket.count,
        }))
        .sort(byLabel);
      const countryTotal =
        facets?.country_code.find((bucket) => bucket.value === sub)?.count ??
        null;
      const name = countryName(sub);
      return {
        id: `${LOCATION_ID}/${sub}`,
        title: name,
        single: true,
        selectedCount: selectedCountry === sub ? 1 : 0,
        options: [
          { value: ANYWHERE, label: `All of ${name}`, count: countryTotal },
          ...cities,
        ],
        isSelected: (value) =>
          value === ANYWHERE ? country === sub && !city : city === value,
        onPick: (value) => {
          if (value === ANYWHERE) onPickCountry(sub);
          else onPickCity(value);
        },
        onClear: onClearLocation,
        clearLabel: "Clear location",
      };
    }

    if (head === POSTED_ID) {
      return {
        id: POSTED_ID,
        title: "Date posted",
        single: true,
        selectedCount: posted ? 1 : 0,
        options: POSTED_OPTIONS.map((option) => ({
          value: option.value === null ? ANYWHERE : String(option.value),
          label: option.label,
          count: null,
        })),
        isSelected: (value) =>
          posted === null ? value === ANYWHERE : value === String(posted),
        onPick: (value) =>
          onPostedChange(value === ANYWHERE ? null : Number(value)),
        onClear: () => onPostedChange(null),
        clearLabel: "Clear date posted",
      };
    }

    const group = FILTER_GROUPS.find((g) => g.key === head);
    if (!group) return null;
    const selected = selections[group.key];
    return {
      id: group.key,
      title: group.title,
      single: false,
      selectedCount: selected.length,
      options: optionsFor(group, facets, selected),
      isSelected: (value) => selected.includes(value),
      onPick: (value) => onToggle(group.key, value),
      onClear: () => onClearGroup(group.key),
      clearLabel: `Clear ${group.title.toLowerCase()}`,
    };
  }, [
    path,
    facets,
    city,
    country,
    selectedCountry,
    posted,
    selections,
    onToggle,
    onClearGroup,
    onPostedChange,
    onPickCity,
    onPickCountry,
    onClearLocation,
  ]);

  const goBack = () => setPath((p) => p.slice(0, -1));

  useEffect(() => {
    if (path.length) backRef.current?.focus();
    else if (lastOpenedRef.current)
      rowRefs.current[lastOpenedRef.current]?.focus();
  }, [path]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (path.length) goBack();
      else onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [path, onClose]);

  return (
    <div
      role="dialog"
      aria-label="Filter jobs"
      className="w-full overflow-hidden rounded-2xl border border-white/20 bg-white/85 shadow-lg shadow-black/10 backdrop-blur-xl"
    >
      <div className="flex items-center justify-between gap-2 border-b border-black/8 px-2 py-2">
        {screen ? (
          <button
            ref={backRef}
            type="button"
            onClick={goBack}
            aria-label={`Back, from ${screen.title}`}
            className="flex min-w-0 items-center gap-1 rounded-lg px-1 py-0.5 text-[11px] font-medium text-gray-700 transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
          >
            <ChevronLeft className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{screen.title}</span>
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
        {screen ? (
          screen.options.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-4 py-6 text-center">
              <p className="text-xs text-gray-500">
                No {screen.title.toLowerCase()} options match your other
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
            <div role={screen.single ? "radiogroup" : "group"}>
              {screen.options.map((option) => (
                <OptionRow
                  key={option.value}
                  option={option}
                  single={screen.single}
                  checked={screen.isSelected(option.value)}
                  onClick={() =>
                    option.drill
                      ? setPath((p) => [...p, option.drill as string])
                      : screen.onPick(option.value)
                  }
                />
              ))}
            </div>
          )
        ) : (
          rootRows.map((row) => (
            <button
              key={row.id}
              ref={(el) => {
                rowRefs.current[row.id] = el;
              }}
              type="button"
              onClick={() => {
                lastOpenedRef.current = row.id;
                setPath([row.id]);
              }}
              aria-label={`${row.title}: ${row.summary}`}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
            >
              <span className="shrink-0 text-xs text-gray-700">
                {row.title}
              </span>
              <span
                className={`ml-auto min-w-0 truncate text-[11px] ${
                  row.active ? "font-medium text-gray-900" : "text-gray-500"
                }`}
              >
                {row.summary}
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
        {screen ? (
          <button
            type="button"
            onClick={screen.onClear}
            disabled={screen.selectedCount === 0}
            className="text-[11px] text-gray-500 transition-colors hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {screen.clearLabel}
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
