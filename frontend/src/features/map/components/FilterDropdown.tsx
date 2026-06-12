import { ROLE_OPTIONS } from "../constants";

type Props = {
  roleFilter: string | null;
  remoteFilter: boolean | null;
  onRoleChange: (value: string | null) => void;
  onRemoteChange: (value: boolean | null) => void;
};

const WORK_OPTIONS: { label: string; value: boolean | null }[] = [
  { label: "All", value: null },
  { label: "Remote", value: true },
  { label: "On-site", value: false },
];

export function FilterDropdown({
  roleFilter,
  remoteFilter,
  onRoleChange,
  onRemoteChange,
}: Props) {
  return (
    <div className="w-full overflow-hidden rounded-xl border border-black/10 bg-white shadow-lg shadow-black/8">
      <div className="border-b border-black/8 px-3 py-2.5">
        <p className="text-[10px] font-medium tracking-widest text-gray-400 uppercase">
          Role
        </p>
        <div className="mt-1.5 flex flex-col gap-0.5">
          {ROLE_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              onClick={() => onRoleChange(opt.value)}
              className={`rounded-lg px-2 py-1.5 text-left text-xs transition-colors ${
                roleFilter === opt.value
                  ? "bg-green-400 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="px-3 py-2.5">
        <p className="text-[10px] font-medium tracking-widest text-gray-400 uppercase">
          Work type
        </p>
        <div className="mt-1.5 flex gap-1.5">
          {WORK_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              onClick={() => onRemoteChange(opt.value)}
              className={`flex-1 rounded-lg py-1.5 text-xs transition-colors ${
                remoteFilter === opt.value
                  ? "bg-green-400 text-white"
                  : "border border-black/8 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
