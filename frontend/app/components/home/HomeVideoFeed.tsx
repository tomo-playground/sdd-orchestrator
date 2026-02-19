"use client";

import WelcomeBar from "./WelcomeBar";
import QuickStatsBar from "./QuickStatsBar";
import ContinueWorkingSection from "./ContinueWorkingSection";
import ShowcaseSection from "./ShowcaseSection";
import Footer from "../ui/Footer";

export default function HomeVideoFeed() {
  return (
    <div className="flex min-h-screen flex-col p-8">
      <div className="space-y-6">
        <WelcomeBar />
        <QuickStatsBar />
        <ContinueWorkingSection />
        <ShowcaseSection />
      </div>
      <Footer />
    </div>
  );
}
