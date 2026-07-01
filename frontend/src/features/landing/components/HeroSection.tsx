import { buttonVariants } from "@/components/ui/button";
import { Globe } from "@/components/ui/globe";
import { Highlighter } from "@/components/ui/highlighter";
import { GitHubIcon } from "@/components/ui/social-icons";
import { DonateModal } from "@/features/landing/components/DonateModal";
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

export function HeroSection() {
  const [stars, setStars] = useState<number | null>(null);
  const [donateOpen, setDonateOpen] = useState(false);

  useEffect(() => {
    fetch(`https://api.github.com/repos/${GITHUB_REPO}`)
      .then((res) => res.json())
      .then((data: { stargazers_count?: number }) => {
        if (typeof data.stargazers_count === "number")
          setStars(data.stargazers_count);
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <DonateModal open={donateOpen} onClose={() => setDonateOpen(false)} />

      <section className="pt-12 pb-12 sm:pt-20 sm:pb-20">
        <div className="mx-auto w-full max-w-2xl px-6 lg:px-0">
          <div className="text-center">
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
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <MapPin className="mr-1.5 size-3.5" aria-hidden="true" />
                Map
              </Link>

              <div className="h-4 w-px bg-black/10" aria-hidden="true" />

              <button
                onClick={() => setDonateOpen(true)}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 cursor-pointer rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <Heart className="mr-1.5 size-3.5" aria-hidden="true" />
                Donate
              </button>

              <div className="h-4 w-px bg-black/10" aria-hidden="true" />

              <a
                href={`https://github.com/${GITHUB_REPO}`}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`View JobDex on GitHub${stars !== null ? ` — ${stars} stars` : ""}`}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "h-8 rounded-full px-3 text-xs font-medium text-gray-600 hover:bg-black hover:text-white",
                )}
              >
                <GitHubIcon className="mr-1.5 size-3.5" />
                {stars !== null ? (
                  <span className="flex items-center gap-1">
                    <Star
                      className="size-3.5 fill-gray-400 stroke-gray-400"
                      aria-hidden="true"
                    />
                    {stars.toLocaleString()}
                  </span>
                ) : (
                  "GitHub"
                )}
              </a>
            </nav>
          </div>

          <div className="mt-8 w-full sm:mt-10">
            <div className="relative mx-auto aspect-square w-full max-w-xl">
              <Globe className="!absolute !inset-0" />
            </div>
          </div>

          <div className="mt-8 flex flex-col items-center gap-3 sm:mt-10 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-6">
            <span className="text-xs text-gray-400">Powered by</span>
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 sm:contents">
              {TECH_STACK.map((tech) => (
                <a
                  key={tech.name}
                  href={tech.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-1.5 opacity-70 transition-opacity hover:opacity-100"
                >
                  <img
                    src={`https://cdn.simpleicons.org/${tech.slug}/${tech.color}`}
                    alt={tech.name}
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

          <nav
            aria-label="Site links"
            className="mt-8 flex items-center justify-center gap-3 border-t border-gray-100 pt-5"
          >
            <Link
              to="/how-it-works"
              className="text-xs text-gray-500 transition-colors hover:text-gray-700"
            >
              How it works
            </Link>
            <span className="text-xs text-gray-300" aria-hidden="true">
              &middot;
            </span>
            <Link
              to="/legal"
              className="text-xs text-gray-500 transition-colors hover:text-gray-700"
            >
              Legal
            </Link>
            <span className="text-xs text-gray-300" aria-hidden="true">
              &middot;
            </span>
            <Link
              to="/faq"
              className="text-xs text-gray-500 transition-colors hover:text-gray-700"
            >
              FAQ
            </Link>
          </nav>
        </div>
      </section>
    </>
  );
}
