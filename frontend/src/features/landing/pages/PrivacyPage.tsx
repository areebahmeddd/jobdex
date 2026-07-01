import { Link } from "react-router-dom";

export default function PrivacyPage() {
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
            Privacy Policy
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Last updated: July 1, 2026
          </p>
        </div>

        <div className="mt-10 space-y-10 text-gray-700">
          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Overview</h2>
            <p className="text-sm leading-relaxed">
              JobDex is a read-only, public tool. You do not need an account to
              use it.{" "}
              <strong>
                We do not collect personal information from visitors.
              </strong>{" "}
              This policy explains what data exists, where it comes from, and
              how it is handled.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Data we do not collect
            </h2>
            <p className="text-sm leading-relaxed">
              JobDex has no user accounts, no login, no sign-up forms, and no
              analytics tracking. We do not set cookies. We do not collect your
              name, email address, IP address, or any other identifying
              information just from browsing the site.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Job listing data
            </h2>
            <p className="text-sm leading-relaxed">
              All job listings on JobDex are sourced from public,
              unauthenticated APIs provided by applicant tracking systems such
              as Greenhouse, Lever, Ashby, Workable, SmartRecruiters, and
              others. This data includes job titles, descriptions, locations,
              and company names. None of it is personal data. We do not store
              resumes, applications, or any information submitted by job
              seekers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Donations</h2>
            <p className="text-sm leading-relaxed">
              Donation payments are processed by Razorpay. When you make a
              donation, you interact directly with Razorpay's checkout
              interface. We never see or store your card number, UPI ID, or bank
              details. Razorpay's privacy policy governs the data they collect
              during payment. We receive only a payment confirmation and a
              transaction ID to verify the signature.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Third-party services
            </h2>
            <p className="text-sm leading-relaxed">
              The site fetches the public GitHub star count for the repository
              from the GitHub API. This request does not include any user data.
              Company metadata such as headquarters location and logo URL is
              sourced from the Clearbit autocomplete API during ingestion. No
              user data is involved in either call.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">
              Changes to this policy
            </h2>
            <p className="text-sm leading-relaxed">
              If this policy changes in a meaningful way, the updated date at
              the top of this page will reflect it. Since we collect no personal
              data, changes are unlikely to affect you in practice.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-gray-900">Contact</h2>
            <p className="text-sm leading-relaxed">
              Questions or concerns can be sent to{" "}
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
