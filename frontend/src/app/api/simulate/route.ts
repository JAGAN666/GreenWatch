import { NextRequest, NextResponse } from "next/server";

const SCORING_URL =
  process.env.SCORING_SERVICE_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${SCORING_URL}/scoring/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: `Scoring service error: ${res.status}`, detail: text },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Simulation proxy error:", error);
    return NextResponse.json(
      { error: "Failed to reach scoring service at " + SCORING_URL },
      { status: 502 }
    );
  }
}
