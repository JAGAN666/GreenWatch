import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-800/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-sm">
            GW
          </div>
          <span className="text-lg font-semibold tracking-tight">GreenWatch</span>
        </div>
        <Link
          href="/map"
          className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Open Workbench
        </Link>
      </nav>

      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center px-6 pt-28 pb-20">
        <div className="inline-flex items-center gap-2 bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 text-xs font-medium px-4 py-1.5 rounded-full mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          AI-Powered Climate Equity Platform
        </div>
        <h1 className="text-6xl sm:text-7xl font-bold tracking-tight leading-tight mb-6">
          Predict. Protect.{" "}
          <span className="text-emerald-400">Plan.</span>
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl leading-relaxed mb-10">
          AI-powered climate investment planning that protects communities.
          Simulate green infrastructure projects and forecast displacement risk
          before a single dollar is spent.
        </p>
        <div className="flex items-center gap-4">
          <Link
            href="/map"
            className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-3.5 rounded-xl text-lg font-semibold transition-colors shadow-lg shadow-emerald-900/30"
          >
            Open Workbench
          </Link>
          <a
            href="#features"
            className="text-gray-400 hover:text-white px-6 py-3.5 rounded-xl text-lg font-medium transition-colors border border-gray-700 hover:border-gray-500"
          >
            Learn More
          </a>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-gray-800/50 bg-gray-900/30">
        <div className="max-w-5xl mx-auto grid grid-cols-3 divide-x divide-gray-800/50">
          <div className="text-center py-8">
            <div className="text-3xl font-bold text-white">85,000+</div>
            <div className="text-sm text-gray-400 mt-1">Census Tracts</div>
          </div>
          <div className="text-center py-8">
            <div className="text-3xl font-bold text-white">7</div>
            <div className="text-sm text-gray-400 mt-1">Federal Data Sources</div>
          </div>
          <div className="text-center py-8">
            <div className="text-3xl font-bold text-white">Real-time</div>
            <div className="text-sm text-gray-400 mt-1">Simulation Engine</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">
            Equitable climate investment, by design
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto">
            Every green infrastructure project has the potential to displace the very
            communities it aims to help. GreenWatch ensures that does not happen.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-red-950/80 border border-red-800/40 flex items-center justify-center text-red-400 text-xl mb-5">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Predict Displacement</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              Our Displacement Risk Score combines census, housing, environmental,
              and health data to identify which communities are most vulnerable to
              green gentrification.
            </p>
          </div>

          {/* Card 2 */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-blue-950/80 border border-blue-800/40 flex items-center justify-center text-blue-400 text-xl mb-5">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18" />
                <path d="M9 21V9" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Simulate Interventions</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              Place parks, greenways, transit stops, and tree plantings on the map.
              Instantly see how each project shifts displacement risk across
              surrounding census tracts.
            </p>
          </div>

          {/* Card 3 */}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-emerald-950/80 border border-emerald-800/40 flex items-center justify-center text-emerald-400 text-xl mb-5">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Optimize for Equity</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              Let AI find the optimal placement that maximizes environmental benefit
              while minimizing displacement risk. Add mitigations to protect the
              most vulnerable neighborhoods.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800/50 py-8 text-center text-sm text-gray-500">
        GreenWatch &mdash; Built for equitable climate action
      </footer>
    </main>
  );
}
