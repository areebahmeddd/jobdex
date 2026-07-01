import { Link } from "react-router-dom";

const DOCUMENTS: {
  title: string;
  description: string;
  href: string;
}[] = [
  {
    title: "Privacy Policy",
    description:
      "What data we collect, how donations are handled through Razorpay, and what third-party services are used.",
    href: "/privacy-policy",
  },
  {
    title: "Terms of Service",
    description:
      "Acceptable use, accuracy limitations on job listings, donation policy, and the MIT open source license.",
    href: "/terms-of-service",
  },
];

export default function LegalPage() {
  return (
    <main className="min-h-screen bg-white font-sans antialiased">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <Link
          to="/"
          className="text-sm text-gray-500 transition-colors hover:text-gray-700"
        >
          &larr; Back to home
        </Link>

        <div className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight text-gray-900">
            Legal
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-gray-500">
            JobDex is a free, open-source tool. No accounts, no tracking, no
            data selling. The documents below cover how the service works from a
            legal standpoint.
          </p>
        </div>

        <div className="mt-10 space-y-4">
          {DOCUMENTS.map((doc) => (
            <Link
              key={doc.href}
              to={doc.href}
              className="group flex flex-col gap-1 rounded-xl border border-gray-200 px-5 py-4 transition-colors hover:border-gray-400"
            >
              <span className="text-sm font-semibold text-gray-900 transition-colors group-hover:text-black">
                {doc.title} &rarr;
              </span>
              <span className="text-sm text-gray-500">{doc.description}</span>
            </Link>
          ))}
        </div>

        <div className="mt-12 border-t border-gray-100 pt-8">
          <p className="text-sm text-gray-500">
            Questions can be sent to{" "}
            <a
              href="mailto:hi@areeb.dev"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              hi@areeb.dev
            </a>{" "}
            or raised by opening an issue on{" "}
            <a
              href="https://github.com/areebahmeddd/jobdex/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              GitHub
            </a>
            .
          </p>
        </div>
      </div>
    </main>
  );
}
