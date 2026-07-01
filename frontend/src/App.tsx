import { Cursor } from "@/components/ui/cursor";
import LandingPage from "@/features/landing/LandingPage";
import FAQPage from "@/features/landing/pages/FAQPage";
import HowItWorksPage from "@/features/landing/pages/HowItWorksPage";
import LegalPage from "@/features/landing/pages/LegalPage";
import NotFoundPage from "@/features/landing/pages/NotFoundPage";
import PrivacyPage from "@/features/landing/pages/PrivacyPage";
import TermsPage from "@/features/landing/pages/TermsPage";
import MapPage from "@/features/map/MapPage";
import { Route, Routes, useLocation } from "react-router-dom";

export default function App() {
  const location = useLocation();
  return (
    <>
      {location.pathname !== "/map" && <Cursor />}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/map" element={<MapPage />} />
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
