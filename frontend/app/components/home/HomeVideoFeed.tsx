"use client";

import ContinueWorkingSection from "./ContinueWorkingSection";
import ShowcaseSection from "./ShowcaseSection";
import QuickActionsWidget from "./QuickActionsWidget";
import QuickStatsWidget from "./QuickStatsWidget";
import Footer from "../ui/Footer";

export default function HomeVideoFeed() {
  return (
    <div className="flex min-h-screen flex-col p-6">
      {/* 2-Column Dashboard */}
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        {/* Left — Primary Content */}
        <div className="min-w-0 space-y-8">
          <ContinueWorkingSection />
          <ShowcaseSection />
        </div>
        {/* Right — Sidebar (lg+) */}
        <div className="space-y-6">
          <QuickActionsWidget />
          <QuickStatsWidget />
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
}
