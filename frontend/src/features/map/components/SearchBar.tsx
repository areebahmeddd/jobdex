import { Search, SlidersHorizontal, X } from "lucide-react";
import { useId, useRef, type KeyboardEvent } from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  onClear: () => void;
  filterOpen: boolean;
  onToggleFilters: () => void;
  activeCount: number;
  className?: string;
  children?: React.ReactNode;
};

export function SearchBar({
  value,
  onChange,
  onSubmit,
  onClear,
  filterOpen,
  onToggleFilters,
  activeCount,
  className = "",
  children,
}: Props) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") onSubmit(value);
    if (e.key === "Escape" && value) {
      onClear();
      inputRef.current?.blur();
    }
  }

  return (
    <div className={`relative ${className}`}>
      <label htmlFor={inputId} className="sr-only">
        Search jobs, companies, and roles
      </label>
      <Search
        className="pointer-events-none absolute top-1/2 left-3.5 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
        aria-hidden="true"
      />
      <input
        id={inputId}
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        autoComplete="off"
        placeholder="Search jobs, companies, roles..."
        className="w-full rounded-full border border-black/10 bg-white py-2.5 pr-16 pl-10 text-sm text-gray-900 shadow-sm shadow-black/5 outline-none placeholder:text-gray-400 focus:border-black/20"
      />

      <div className="absolute top-1/2 right-2.5 flex -translate-y-1/2 items-center gap-1">
        {value && (
          <button
            type="button"
            onClick={onClear}
            aria-label="Clear search"
            className="flex h-5 w-5 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-700"
          >
            <X className="h-3 w-3" aria-hidden="true" />
          </button>
        )}
        <button
          type="button"
          onClick={onToggleFilters}
          aria-expanded={filterOpen}
          aria-label={
            activeCount > 0 ? `Filters, ${activeCount} active` : "Filters"
          }
          className={`relative flex h-6 items-center gap-1 rounded-full px-1.5 transition-colors ${
            activeCount > 0 || filterOpen
              ? "bg-black text-white"
              : "text-gray-400 hover:bg-black/5 hover:text-gray-700"
          }`}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          {activeCount > 0 && (
            <span className="text-[10px] font-medium tabular-nums">
              {activeCount}
            </span>
          )}
        </button>
      </div>

      {children}
    </div>
  );
}
