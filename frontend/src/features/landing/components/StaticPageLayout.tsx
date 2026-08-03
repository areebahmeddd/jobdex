import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

const FOOTER_LINKS: { label: string; to: string }[] = [
  { label: "Home", to: "/" },
  { label: "Map", to: "/map" },
  { label: "How it works", to: "/how-it-works" },
  { label: "FAQ", to: "/faq" },
  { label: "Legal", to: "/legal" },
  { label: "Privacy", to: "/privacy-policy" },
  { label: "Terms", to: "/terms-of-service" },
];

interface StaticPageLayoutProps {
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}

export function StaticPageLayout({
  title,
  intro,
  children,
}: StaticPageLayoutProps) {
  const { pathname } = useLocation();
  const siblings = FOOTER_LINKS.filter((link) => link.to !== pathname);

  return (
    <main className="bg-white font-sans antialiased">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col px-6 pt-16 pb-10">
        <Link
          to="/"
          className="group inline-flex w-fit items-center gap-1.5 py-1 text-sm text-gray-500 transition-colors hover:text-gray-900"
        >
          <ArrowLeft
            className="h-3.5 w-3.5 transition-transform duration-200 group-hover:-translate-x-0.5"
            aria-hidden="true"
          />
          Back to home
        </Link>

        <header className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight text-gray-900">
            {title}
          </h1>
          {intro && (
            <p className="mt-2 text-sm leading-relaxed text-gray-500">
              {intro}
            </p>
          )}
        </header>

        <div className="mt-10 flex-1">{children}</div>

        <footer className="mt-12 border-t border-gray-100 pt-6">
          <nav
            aria-label="Site links"
            className="flex flex-wrap justify-center gap-x-4 gap-y-1"
          >
            {siblings.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="py-1 text-xs text-gray-500 transition-colors hover:text-gray-900"
              >
                {link.label}
              </Link>
            ))}
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
    </main>
  );
}
