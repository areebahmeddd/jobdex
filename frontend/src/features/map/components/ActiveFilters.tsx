import type { FilterChip } from "@/features/map/hooks/useJobFilters";
import { MapPin, X } from "lucide-react";

type Props = {
  city: string | null;
  onClearCity: () => void;
  chips: FilterChip[];
  onClearAll: () => void;
};

function Chip({
  icon,
  group,
  label,
  onRemove,
  removeLabel,
}: {
  icon?: React.ReactNode;
  group?: string;
  label: string;
  onRemove: () => void;
  removeLabel: string;
}) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-black/10 bg-white/90 py-1 pr-1 pl-2 text-[11px] whitespace-nowrap text-gray-700 shadow-sm shadow-black/5">
      {icon}
      {group && <span className="text-gray-400">{group}</span>}
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={removeLabel}
        className="flex h-4 w-4 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-700"
      >
        <X className="h-2.5 w-2.5" aria-hidden="true" />
      </button>
    </span>
  );
}

export function ActiveFilters({ city, onClearCity, chips, onClearAll }: Props) {
  if (!city && chips.length === 0) return null;

  return (
    <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto">
      {city && (
        <Chip
          icon={
            <MapPin className="h-2.5 w-2.5 text-gray-400" aria-hidden="true" />
          }
          label={city}
          onRemove={onClearCity}
          removeLabel={`Remove ${city} filter`}
        />
      )}
      {chips.map((chip) => (
        <Chip
          key={chip.id}
          group={chip.group}
          label={chip.label}
          onRemove={chip.remove}
          removeLabel={`Remove ${chip.group ?? ""} ${chip.label} filter`}
        />
      ))}
      {chips.length > 1 && (
        <button
          type="button"
          onClick={onClearAll}
          className="shrink-0 px-1.5 text-[11px] whitespace-nowrap text-gray-500 transition-colors hover:text-gray-900"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
