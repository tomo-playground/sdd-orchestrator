"use client";

import ShowcaseSection from "./ShowcaseSection";
import QuickActionsWidget from "./QuickActionsWidget";
import QuickStatsWidget from "./QuickStatsWidget";
import Footer from "../ui/Footer";

export default function HomeVideoFeed() {
  return (
    <div className="flex min-h-screen flex-col p-6">
      {/* Showcase Section - Shows top 3 recent videos or empty state */}
      <ShowcaseSection />

      {/* Quick Actions - Navigation shortcuts */}
      <QuickActionsWidget />

      {/* Quick Stats - Library overview */}
      <QuickStatsWidget />

      {/* Footer */}
      <Footer />
    </div>
  );
}
