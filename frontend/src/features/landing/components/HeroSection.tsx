import { buttonVariants } from "@/components/ui/button";
import { Globe } from "@/components/ui/globe";
import { Highlighter } from "@/components/ui/highlighter";
import { GitHubIcon } from "@/components/ui/social-icons";
import { DonateModal } from "@/features/landing/components/DonateModal";
import { importMapPage } from "@/features/map/lazy";
import { GITHUB_REPO } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Heart, MapPin, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const TECH_STACK: {
  name: string;
  slug: string;
  href: string;
  color: string;
}[] = [
  {
    name: "FastAPI",
    slug: "fastapi",
    href: "https://fastapi.tiangolo.com",
    color: "009688",
  },
  {
    name: "PostgreSQL",
    slug: "postgresql",
    href: "https://postgresql.org",
    color: "4169E1",
  },
  { name: "React", slug: "react", href: "https://react.dev", color: "61DAFB" },
  {
    name: "OpenStreetMap",
    slug: "openstreetmap",
    href: "https://openstreetmap.org",
    color: "7EBC6F",
  },
  {
    name: "shadcn/ui",
    slug: "shadcnui",
    href: "https://ui.shadcn.com",
    color: "000000",
  },
];

const prefetchMap = () => void importMapPage();

export function HeroSection() {
  const [stars, setStars] = useState<number | null>(null);
  const [donateOpen, setDonateOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    fetch(`https://api.github.com/repos/${GITHUB_REPO}`, {
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data: { stargazers_count?: number }) => {
        if (typeof data.stargazers_count === "number")
          setStars(data.stargazers_count);
      })
      .catch(() => {});

    return () => controller.abort();
  }, []);

  return (
    <>
      <DonateModal open={donateOpen} onClose={() => setDonateOpen(false)} />

      <section className="pt-12 pb-10 sm:pt-20 sm:pb-14">
        <div className="mx-auto w-full max-w-2xl px-6 lg:px-0">
          <header className="text-center">
            <h1 className="mx-auto max-w-xl text-4xl font-medium tracking-tight text-balance text-gray-950 sm:text-5xl">
              A global index of startup hiring by city.
            </h1>
            <p className="mx-auto mt-5 max-w-md text-lg text-balance text-gray-500">
              Aggregates startup jobs from hundreds of hiring sources onto a{" "}
              <Highlighter
                action="underline"
                color="#111111"
                strokeWidth={2}
                animationDuration={600}
              >
                single interactive world map
              </Highlighter>
              .
            </p>

            <nav
              aria-label="Primary actions"
              className="mt-6 inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/90 px-2.5 py-1.5 shadow-lg shadow-black/8 backdrop-blur-md"
            >
              <Link
                to="/map"
                onMouseEnter={prefetchMap}
                onFocus={prefetchMap}
                onTouchStart={prefetchMap}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 gap-1.5 rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <MapPin className="size-3.5" aria-hidden="true" />
                Map
              </Link>

              <div className="h-4 w-px bg-black/10" aria-hidden="true" />

              <button
                type="button"
                onClick={() => setDonateOpen(true)}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 cursor-pointer gap-1.5 rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <Heart className="size-3.5" aria-hidden="true" />
                Donate
              </button>

              <div className="h-4 w-px bg-black/10" aria-hidden="true" />

              <a
                href={`https://github.com/${GITHUB_REPO}`}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`View JobDex on GitHub${stars !== null ? ` - ${stars} stars` : ""}`}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 gap-1.5 rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <GitHubIcon className="size-3.5" />
                {stars !== null ? (
                  <span className="inline-flex items-center gap-1 tabular-nums">
                    <Star
                      className="size-3 fill-current stroke-current opacity-60"
                      aria-hidden="true"
                    />
                    {stars.toLocaleString()}
                  </span>
                ) : (
                  "GitHub"
                )}
              </a>
            </nav>
          </header>

          <div className="relative mx-auto mt-8 aspect-square w-full max-w-xl sm:mt-10">
            <Globe />
          </div>

          <div className="mt-8 flex flex-col items-center gap-3 sm:mt-10 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-x-6 sm:gap-y-1">
            <span className="text-xs text-gray-500">Powered by</span>
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 sm:contents">
              {TECH_STACK.map((tech) => (
                <a
                  key={tech.name}
                  href={tech.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-1.5 py-1 opacity-70 transition-opacity hover:opacity-100"
                >
                  <img
                    src={`https://cdn.simpleicons.org/${tech.slug}/${tech.color}`}
                    alt=""
                    aria-hidden="true"
                    width={14}
                    height={14}
                    className="size-3.5"
                  />
                  <span className="text-xs text-gray-600 transition-colors group-hover:text-gray-900">
                    {tech.name}
                  </span>
                </a>
              ))}
            </div>
          </div>

          <footer className="mt-8 border-t border-gray-100 pt-4">
            <nav
              aria-label="Site links"
              className="flex items-center justify-center gap-3"
            >
              <Link
                to="/how-it-works"
                className="px-1 py-1 text-xs text-gray-500 transition-colors hover:text-gray-900"
              >
                How it works
              </Link>
              <span className="text-xs text-gray-300" aria-hidden="true">
                &middot;
              </span>
              <Link
                to="/legal"
                className="px-1 py-1 text-xs text-gray-500 transition-colors hover:text-gray-900"
              >
                Legal
              </Link>
              <span className="text-xs text-gray-300" aria-hidden="true">
                &middot;
              </span>
              <Link
                to="/faq"
                className="px-1 py-1 text-xs text-gray-500 transition-colors hover:text-gray-900"
              >
                FAQ
              </Link>
            </nav>

            <p className="mt-2 text-center text-xs text-gray-500">
              A{" "}
              <a
                href="https://1mindlabs.org"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                1Mind Labs
              </a>{" "}
              project
            </p>
          </footer>
        </div>
      </section>
    </>
  );
}
