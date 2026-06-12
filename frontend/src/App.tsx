import LandingPage from "@/pages/LandingPage";
import MapPage from "@/pages/MapPage";
import { Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/map" element={<MapPage />} />
    </Routes>
  );
}
