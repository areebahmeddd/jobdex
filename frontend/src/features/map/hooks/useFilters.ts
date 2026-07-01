import { useState } from "react";

export function useFilters() {
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [remoteFilter, setRemoteFilter] = useState<boolean | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);

  return {
    roleFilter,
    setRoleFilter,
    remoteFilter,
    setRemoteFilter,
    filterOpen,
    setFilterOpen,
  };
}
