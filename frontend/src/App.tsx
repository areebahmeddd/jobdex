import LandingPage from "@/features/landing/LandingPage";
import MapPage from "@/features/map/MapPage";
import { Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/map" element={<MapPage />} />
    </Routes>
  );
}
