import { Link } from "react-router-dom";

export default function TermsPage() {
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
            Terms of Service
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Last updated: July 1, 2026
          </p>
        </div>

        <div className="mt-10 space-y-10 text-gray-700">
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Overview</h2>
            <p className="text-sm leading-relaxed">
              JobDex is a free, open-source tool for browsing startup job
              listings by city. By using the site, you agree to these terms. If
              you do not agree, please do not use the service.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Use of the service
            </h2>
            <p className="text-sm leading-relaxed">
              JobDex is provided for personal, informational use. You may not
              use automated tools to scrape or bulk-download data from this
              site. The underlying API is public and documented for legitimate
              integrations. You may not use the service for any unlawful purpose
              or in a way that could harm the platform or its users.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Job listing accuracy
            </h2>
            <p className="text-sm leading-relaxed">
              Job listings are pulled from third-party applicant tracking
              systems and refreshed approximately every six hours. We do not
              create, verify, or endorse any listing. A role shown as open may
              have already been filled. JobDex is not a recruiter, employer, or
              staffing agency. We have no involvement in any hiring process.
            </p>
            <p className="text-sm leading-relaxed">
              <strong>
                Always verify a listing directly on the company's website before
                applying.
              </strong>
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Donations</h2>
            <p className="text-sm leading-relaxed">
              Donations support the running costs of the project. They are{" "}
              <strong>voluntary and non-refundable</strong>. Payments are
              processed by Razorpay. Donating does not entitle you to any
              service, feature, or preference. JobDex is not a registered
              non-profit.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Open source
            </h2>
            <p className="text-sm leading-relaxed">
              The source code for JobDex is published under the MIT License on{" "}
              <a
                href="https://github.com/areebahmeddd/jobdex"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                GitHub
              </a>
              . The MIT License governs use, modification, and distribution of
              the code. These terms of service apply only to use of the hosted
              website at jobdex.1mindlabs.org.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Disclaimer
            </h2>
            <p className="text-sm leading-relaxed">
              JobDex is provided "as is" without any warranty of any kind. We
              make no guarantees about uptime, data accuracy, or completeness of
              listings. We are not liable for any decisions made based on
              information found on this site.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Changes to these terms
            </h2>
            <p className="text-sm leading-relaxed">
              We may update these terms from time to time. Continued use of the
              site after changes are posted means you accept the updated terms.
              The date at the top of this page reflects the most recent
              revision.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Contact</h2>
            <p className="text-sm leading-relaxed">
              Questions about these terms can be sent to{" "}
              <a
                href="mailto:hi@areeb.dev"
                className="underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                hi@areeb.dev
              </a>{" "}
              or raised by opening an issue on{" "}
              <a
                href="https://github.com/areebahmeddd/jobdex"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                GitHub
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
