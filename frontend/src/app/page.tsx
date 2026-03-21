import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-5xl font-bold tracking-tight mb-4">GreenWatch</h1>
      <p className="text-xl text-gray-400 max-w-2xl text-center mb-8">
        The equity simulation engine for climate investment. Predict
        displacement risk before spending. Protect the communities you serve.
      </p>
      <Link
        href="/map"
        className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-3 rounded-lg text-lg font-medium transition-colors"
      >
        Open Simulation Workbench
      </Link>
    </main>
  );
}
