import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GreenWatch — Climate Equity Simulation Engine",
  description:
    "Predict gentrification risk from climate investments. Simulate interventions. Recommend mitigations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-950 text-gray-100">{children}</body>
    </html>
  );
}
