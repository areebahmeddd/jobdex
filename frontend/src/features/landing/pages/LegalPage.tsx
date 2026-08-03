import { StaticPageLayout } from "@/features/landing/components/StaticPageLayout";
import { ArrowRight } from "lucide-react";
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
    <StaticPageLayout
      title="Legal"
      intro="JobDex is a free, open-source tool. No accounts, no tracking, no data selling. The documents below cover how the service works from a legal standpoint."
    >
      <div className="space-y-4">
        {DOCUMENTS.map((doc) => (
          <Link
            key={doc.href}
            to={doc.href}
            className="group flex flex-col gap-1 rounded-xl border border-gray-200 px-5 py-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md"
          >
            <span className="flex items-center justify-between text-sm font-semibold text-gray-900 transition-colors group-hover:text-black">
              {doc.title}
              <ArrowRight
                className="h-3.5 w-3.5 text-gray-500 transition-transform duration-200 group-hover:translate-x-1 group-hover:text-gray-900"
                aria-hidden="true"
              />
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
    </StaticPageLayout>
  );
}
