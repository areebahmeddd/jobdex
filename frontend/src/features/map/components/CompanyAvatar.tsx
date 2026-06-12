import { useState } from "react";

type Props = {
  name: string;
  slug: string;
  logoUrl: string | null;
  size?: number;
};

function buildSources(logoUrl: string | null, slug: string): string[] {
  const cleaned = slug.replace(/[^a-z0-9-]/gi, "").toLowerCase();
  const sources: string[] = [];
  if (logoUrl) sources.push(logoUrl);
  sources.push(`https://logo.clearbit.com/${cleaned}.com`);
  sources.push(
    `https://www.google.com/s2/favicons?domain=${cleaned}.com&sz=128`,
  );
  return sources;
}

export function CompanyAvatar({ name, slug, logoUrl, size = 32 }: Props) {
  const sources = buildSources(logoUrl, slug);
  const [srcIndex, setSrcIndex] = useState(0);

  if (srcIndex < sources.length) {
    return (
      <img
        src={sources[srcIndex]}
        alt={name}
        width={size}
        height={size}
        onError={() => setSrcIndex((i) => i + 1)}
        className="shrink-0 rounded bg-gray-50 object-contain"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className="flex shrink-0 items-center justify-center rounded bg-gray-100 font-medium text-gray-400"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.42) }}
    >
      {name.charAt(0).toUpperCase()}
    </div>
  );
}
