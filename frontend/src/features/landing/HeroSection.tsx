import { buttonVariants } from "@/components/ui/button";
import { Globe } from "@/components/ui/globe";
import { Highlighter } from "@/components/ui/highlighter";
import { DonateModal } from "@/features/landing/DonateModal";
import { cn } from "@/lib/utils";
import { Heart, MapPin, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const GITHUB_REPO = "areebahmeddd/jobdex";

const TECH_STACK = [
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

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2C6.477 2 2 6.484 2 12.021c0 4.428 2.865 8.184 6.839 9.504.5.092.682-.217.682-.482 0-.237-.009-.868-.013-1.703-2.782.605-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.026 2.747-1.026.546 1.378.202 2.397.1 2.65.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482C19.138 20.2 22 16.447 22 12.021 22 6.484 17.523 2 12 2z" />
    </svg>
  );
}

export function HeroSection() {
  const [stars, setStars] = useState<number | null>(null);
  const [donateOpen, setDonateOpen] = useState(false);

  useEffect(() => {
    fetch(`https://api.github.com/repos/${GITHUB_REPO}`)
      .then((res) => res.json())
      .then((data) => {
        if (typeof data.stargazers_count === "number")
          setStars(data.stargazers_count);
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <DonateModal open={donateOpen} onClose={() => setDonateOpen(false)} />

      <section className="pt-12 pb-8 sm:pt-20 sm:pb-12">
        <div className="mx-auto w-full max-w-2xl px-6 md:px-4 lg:px-0">
          <div className="text-center">
            <h1 className="mx-auto max-w-xl text-4xl font-medium tracking-tight text-balance text-gray-950 sm:text-5xl">
              A global index of startup hiring by city.
            </h1>
            <p className="text-muted-foreground mx-auto mt-4 max-w-md text-lg text-balance">
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
              className="mt-6 inline-flex items-center gap-1 rounded-full border border-black/10 bg-white/90 px-2 py-1.5 shadow-lg shadow-black/8 backdrop-blur-md"
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

          <div className="relative mt-6 w-full sm:mt-8">
            <div className="mx-auto aspect-square w-full max-w-xl">
              <Globe className="!absolute !inset-0" />
            </div>
          </div>

          <div className="mt-8 flex flex-col items-center gap-2 sm:mt-16 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-6">
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
        </div>
      </section>
    </>
  );
}
