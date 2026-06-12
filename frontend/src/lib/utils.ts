import { formatDistanceToNow, isValid, parseISO } from "date-fns";

/**
 * Utility for combining Tailwind CSS class names.
 */
export function cn(
  ...inputs: (string | undefined | null | boolean | Record<string, boolean>)[]
) {
  const classes: string[] = [];
  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === "string") {
      classes.push(input);
    } else if (typeof input === "object") {
      for (const [key, value] of Object.entries(input)) {
        if (value) {
          classes.push(key);
        }
      }
    }
  }
  return classes.join(" ");
}

/**
 * Formats a raw database date string into relative time (e.g. "2 hours ago" or "3 days ago").
 */
export function formatRelativeTime(
  dateString: string | undefined | null,
): string {
  if (!dateString) return "Recent";
  try {
    const parsed = parseISO(dateString);
    if (!isValid(parsed)) return "Recent";
    return formatDistanceToNow(parsed, { addSuffix: true });
  } catch (e) {
    return "Recent";
  }
}

/**
 * Maps a seniority enum rank to designated high-contrast Tailwind styling colors.
 */
export function getSeniorityColor(seniority: string | null | undefined): {
  bg: string;
  text: string;
  border: string;
} {
  const norm = (seniority || "").toLowerCase();

  if (norm === "intern" || norm === "junior") {
    return {
      bg: "bg-blue-50 dark:bg-blue-950/45",
      text: "text-blue-700 dark:text-blue-400",
      border: "border-blue-200 dark:border-blue-900/50",
    };
  }

  if (norm === "mid") {
    return {
      bg: "bg-green-50 dark:bg-green-950/45",
      text: "text-green-700 dark:text-green-400",
      border: "border-green-200 dark:border-green-900/50",
    };
  }

  if (norm === "senior") {
    return {
      bg: "bg-amber-50 dark:bg-amber-950/45",
      text: "text-amber-700 dark:text-amber-400",
      border: "border-amber-200 dark:border-amber-900/50",
    };
  }

  if (norm === "lead" || norm === "staff" || norm === "principal") {
    return {
      bg: "bg-violet-50 dark:bg-violet-950/45",
      text: "text-violet-700 dark:text-violet-400",
      border: "border-violet-200 dark:border-violet-900/50",
    };
  }

  if (norm === "director" || norm === "vp" || norm === "c-level") {
    return {
      bg: "bg-red-50 dark:bg-red-950/45",
      text: "text-red-700 dark:text-red-400",
      border: "border-red-200 dark:border-red-900/50",
    };
  }

  return {
    bg: "bg-gray-50 dark:bg-gray-800/50",
    text: "text-gray-600 dark:text-gray-300",
    border: "border-gray-200 dark:border-gray-700",
  };
}
