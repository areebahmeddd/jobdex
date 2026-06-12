import { Cursor } from "@/components/ui/cursor";
import { HeroSection } from "@/features/landing/HeroSection";

export default function LandingPage() {
  return (
    <main className="w-full bg-white font-sans antialiased">
      <Cursor />
      <HeroSection />
    </main>
  );
}
