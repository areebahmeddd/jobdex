import { Link } from "react-router-dom";

const SECTIONS: {
  heading: string;
  questions: { q: string; a: React.ReactNode }[];
}[] = [
  {
    heading: "Using JobDex",
    questions: [
      {
        q: "Is it free to use?",
        a: "Yes. JobDex is completely free. No account, no sign-up, no paywall.",
      },
      {
        q: "How do I find jobs in a specific city?",
        a: "Open the map and click any city pin. The panel on the left will load companies currently hiring in that city. From there you can browse roles, filter by category or remote status, and click through to the original job posting.",
      },
    ],
  },
  {
    heading: "Job listings",
    questions: [
      {
        q: "How often are listings updated?",
        a: "The ingestion pipeline runs every six hours and crawls all active companies. When a role disappears from the source, it is marked inactive rather than deleted.",
      },
      {
        q: "Why can't I find a company I'm looking for?",
        a: (
          <>
            JobDex only indexes companies that use a{" "}
            <a
              href="https://github.com/areebahmeddd/jobdex#data-sources"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              supported ATS
            </a>
            . If a company uses a different ATS or posts jobs only on their own
            website, it will not appear on the map.
          </>
        ),
      },
    ],
  },
  {
    heading: "Data and privacy",
    questions: [
      {
        q: "Do you collect any personal data?",
        a: (
          <>
            No. JobDex has no user accounts, no login, and no analytics
            tracking. We do not collect your name, email, IP address, or any
            other identifying information. See the{" "}
            <Link
              to="/privacy-policy"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              Privacy Policy
            </Link>{" "}
            for the full details.
          </>
        ),
      },
      {
        q: "Do you store my searches or map activity?",
        a: "No. All filtering and search happens as API requests from your browser. Nothing is stored on our end.",
      },
    ],
  },
  {
    heading: "Donations",
    questions: [
      {
        q: "Are donations refundable?",
        a: "No. Donations are voluntary and non-refundable. Payments are processed by Razorpay and we have no ability to issue refunds once a transaction is completed.",
      },
      {
        q: "What does my donation go toward?",
        a: "Running costs: server hosting, database, and the domain. JobDex is a side project with no venture backing. Donations help keep it online and free.",
      },
    ],
  },
  {
    heading: "Open source",
    questions: [
      {
        q: "Can I contribute?",
        a: (
          <>
            Yes. The full source code is on GitHub under the MIT license. You
            can open issues, submit pull requests, or add support for a new ATS
            provider. See the{" "}
            <a
              href="https://github.com/areebahmeddd/jobdex/blob/main/docs/CONTRIBUTING.md"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              contributing guide
            </a>{" "}
            for conventions and setup instructions.
          </>
        ),
      },
      {
        q: "Can I self-host JobDex?",
        a: "Yes. The repo includes a docker-compose.yaml that spins up the full stack locally.",
      },
    ],
  },
];

export default function FAQPage() {
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
            Frequently Asked Questions
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Common questions about JobDex.
          </p>
        </div>

        <div className="mt-10 space-y-10">
          {SECTIONS.map((section) => (
            <section key={section.heading} className="space-y-1">
              <h2 className="mb-3 text-base font-semibold text-gray-900">
                {section.heading}
              </h2>
              {section.questions.map((item) => (
                <details
                  key={item.q}
                  className="group border-b border-gray-100 py-3"
                >
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                    <span className="text-sm font-medium text-gray-900">
                      {item.q}
                    </span>
                    <span className="shrink-0 text-sm text-gray-500 transition-transform group-open:rotate-45">
                      +
                    </span>
                  </summary>
                  <p className="mt-3 pr-6 text-sm leading-relaxed text-gray-600">
                    {item.a}
                  </p>
                </details>
              ))}
            </section>
          ))}
        </div>

        <div className="mt-16 border-t border-gray-100 pt-8">
          <p className="text-sm text-gray-500">
            Can't find what you're looking for? Email{" "}
            <a
              href="mailto:hi@areeb.dev"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              hi@areeb.dev
            </a>{" "}
            or{" "}
            <a
              href="https://github.com/areebahmeddd/jobdex/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline underline-offset-2 transition-colors hover:text-gray-600"
            >
              open an issue on GitHub
            </a>
            .
          </p>
        </div>
      </div>
    </main>
  );
}
