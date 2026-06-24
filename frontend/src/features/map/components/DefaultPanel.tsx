import { MapPin } from "lucide-react";

export function DefaultPanel() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
      <div className="flex h-10 w-10 items-center justify-center">
        <MapPin className="h-5 w-5 text-gray-400" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-700">
          Explore jobs worldwide
        </p>
        <p className="mt-1 text-xs text-gray-400">
          Click any company pin or search to find open roles
        </p>
      </div>
    </div>
  );
}
