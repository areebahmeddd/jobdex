import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-white px-6 font-sans antialiased">
      <div className="text-center">
        <p className="text-sm font-semibold tracking-widest text-gray-500 uppercase">
          404
        </p>
        <h1 className="mt-4 text-5xl font-semibold tracking-tight text-gray-900 sm:text-6xl">
          Page not found
        </h1>
        <p className="mt-4 text-base text-gray-500">
          Sorry, we couldn&apos;t find the page you&apos;re looking for.
        </p>
        <div className="mt-8 flex items-center justify-center gap-6">
          <Link
            to="/"
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-700"
          >
            Go back home
          </Link>
          <Link
            to="/map"
            className="text-sm font-medium text-gray-900 transition-colors hover:text-gray-600"
          >
            Explore map &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
