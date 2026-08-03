import { Cursor } from "@/components/ui/cursor";
import LandingPage from "@/features/landing/LandingPage";
import FAQPage from "@/features/landing/pages/FAQPage";
import HowItWorksPage from "@/features/landing/pages/HowItWorksPage";
import LegalPage from "@/features/landing/pages/LegalPage";
import NotFoundPage from "@/features/landing/pages/NotFoundPage";
import PrivacyPage from "@/features/landing/pages/PrivacyPage";
import TermsPage from "@/features/landing/pages/TermsPage";
import { importMapPage } from "@/features/map/lazy";
import { canonicalFor, NOT_FOUND_META, ROUTE_META } from "@/lib/routeMeta";
import { lazy, Suspense, useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

const MapPage = lazy(importMapPage);

function setMeta(selector: string, content: string) {
  document.head.querySelector(selector)?.setAttribute("content", content);
}

function RouteEffects() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    const known = pathname in ROUTE_META;
    const meta = known ? ROUTE_META[pathname] : NOT_FOUND_META;

    document.title = meta.title;
    setMeta('meta[name="description"]', meta.description);
    setMeta('meta[property="og:title"]', meta.title);
    setMeta('meta[property="og:description"]', meta.description);
    setMeta('meta[name="twitter:title"]', meta.title);
    setMeta('meta[name="twitter:description"]', meta.description);

    if (known) {
      const canonical = canonicalFor(pathname);
      document.head
        .querySelector('link[rel="canonical"]')
        ?.setAttribute("href", canonical);
      setMeta('meta[property="og:url"]', canonical);
    }
  }, [pathname]);

  useEffect(() => {
    if (hash) return;
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname, hash]);

  return null;
}

export default function App() {
  const location = useLocation();
  return (
    <>
      <RouteEffects />
      {location.pathname !== "/map" && <Cursor />}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/map"
          element={
            <Suspense
              fallback={
                <div
                  className="grid min-h-screen place-items-center bg-white text-sm text-gray-500"
                  role="status"
                >
                  Loading map…
                </div>
              }
            >
              <MapPage />
            </Suspense>
          }
        />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/legal" element={<LegalPage />} />
        <Route path="/privacy-policy" element={<PrivacyPage />} />
        <Route path="/terms-of-service" element={<TermsPage />} />
        <Route path="/faq" element={<FAQPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  );
}
