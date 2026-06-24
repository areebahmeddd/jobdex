import { useState } from "react";

type Props = {
  name: string;
  logoUrl: string | null;
  size?: number;
};

export function CompanyAvatar({ name, logoUrl, size = 32 }: Props) {
  const [failed, setFailed] = useState(false);

  if (logoUrl && !failed) {
    return (
      <img
        src={logoUrl}
        alt={name}
        width={size}
        height={size}
        onError={() => setFailed(true)}
        className="shrink-0 rounded bg-gray-50 object-contain"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className="flex shrink-0 items-center justify-center rounded bg-gray-100 font-medium text-gray-500"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.42) }}
    >
      {name.charAt(0).toUpperCase()}
    </div>
  );
}
