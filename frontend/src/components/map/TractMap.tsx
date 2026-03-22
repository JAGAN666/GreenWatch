"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import type { TractProperties, Intervention } from "@/lib/types";
import { STATE_NAMES, IMPACT_RADII } from "@/lib/constants";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

const INTERVENTION_COLORS: Record<string, string> = {
  park: "#22c55e",
  greenway: "#84cc16",
  transit_stop: "#3b82f6",
  tree_planting: "#166534",
  flood_infrastructure: "#22d3ee",
  green_roof: "#14b8a6",
};

interface TractMapProps {
  tracts: unknown;
  selectedTract: TractProperties | null;
  onTractClick: (tract: TractProperties) => void;
  onMapClick: (lat: number, lng: number) => void;
  metric: "drs" | "ebs";
  interventions: Intervention[];
  predictedScores?: Record<string, number>;
  showPredicted?: boolean;
  placing?: boolean;
  onBoundsChange?: (bounds: {
    min_lat: number;
    min_lng: number;
    max_lat: number;
    max_lng: number;
  }) => void;
}

export default function TractMap({
  selectedTract,
  onTractClick,
  onMapClick,
  metric,
  interventions,
  placing,
  onBoundsChange,
}: TractMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Use refs for callbacks so map event handlers always get latest
  const onTractClickRef = useRef(onTractClick);
  const onMapClickRef = useRef(onMapClick);
  const placingRef = useRef(placing);
  const onBoundsChangeRef = useRef(onBoundsChange);
  onTractClickRef.current = onTractClick;
  onMapClickRef.current = onMapClick;
  placingRef.current = placing;
  onBoundsChangeRef.current = onBoundsChange;

  // Helper to emit bounds
  function emitBounds(m: maplibregl.Map) {
    if (!onBoundsChangeRef.current) return;
    const bounds = m.getBounds();
    onBoundsChangeRef.current({
      min_lat: bounds.getSouth(),
      min_lng: bounds.getWest(),
      max_lat: bounds.getNorth(),
      max_lng: bounds.getEast(),
    });
  }

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);

    const origin =
      typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:3000";

    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          "raster-tiles": {
            type: "raster",
            tiles: [
              "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
          },
          tracts: {
            type: "vector",
            url: "pmtiles://https://pub-fc4358ea50ca43dfa65d6ec0b1f2cb8f.r2.dev/us_tracts.pmtiles",
          },
        },
        layers: [
          { id: "basemap", type: "raster", source: "raster-tiles" },
        ],
      },
      center: [-98.5, 39.8],
      zoom: 4,
    });

    m.on("load", () => {
      m.addLayer({
        id: "tract-fill",
        type: "fill",
        source: "tracts",
        "source-layer": "tracts",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "drs"],
            0,
            "#00c800",
            25,
            "#c8c800",
            50,
            "#ffa500",
            75,
            "#ff0000",
            100,
            "#8b0000",
          ],
          "fill-opacity": 0.7,
        },
      });

      m.addLayer({
        id: "tract-border",
        type: "line",
        source: "tracts",
        "source-layer": "tracts",
        paint: { "line-color": "#333", "line-width": 0.5 },
      });

      m.addLayer({
        id: "tract-highlight",
        type: "line",
        source: "tracts",
        "source-layer": "tracts",
        paint: { "line-color": "#ffffff", "line-width": 3 },
        filter: ["==", "geoid", ""],
      });

      setMapLoaded(true);
      emitBounds(m);
    });

    // Emit bounds on move
    m.on("moveend", () => {
      emitBounds(m);
    });

    // Click handler
    m.on("click", (e) => {
      if (placingRef.current) {
        onMapClickRef.current(e.lngLat.lat, e.lngLat.lng);
        return;
      }

      const features = m.queryRenderedFeatures(e.point, {
        layers: ["tract-fill"],
      });

      if (features && features.length > 0) {
        const props = features[0].properties;
        if (props) {
          onTractClickRef.current({
            geoid: props.geoid,
            county_name: props.county || "",
            name: props.geoid,
            drs_composite: props.drs || 0,
            drs_vulnerability: 0,
            drs_market_pressure: 0,
            drs_green_proximity: 0,
            drs_classification: props.drs_class || "low",
            ebs_composite: props.ebs || 0,
            ebs_air_quality: 0,
            ebs_green_infra: 0,
            ebs_climate_resilience: 0,
            ebs_health: 0,
            median_rent: props.rent || null,
            median_home_value: null,
            median_household_income: null,
            pct_renters: props.pct_rent || null,
            pct_rent_burdened: props.pct_burden || null,
            pct_nonwhite: props.pct_nonwh || null,
            total_population: props.pop || null,
            asthma_prevalence: null,
            eviction_rate: null,
            tree_canopy_pct: null,
            cejst_disadvantaged: false,
            accelerating_risk: props.accel_risk || false,
          } as TractProperties);
        }
      } else {
        onMapClickRef.current(e.lngLat.lat, e.lngLat.lng);
      }
    });

    // Hover tooltip
    m.on("mousemove", "tract-fill", (e) => {
      m.getCanvas().style.cursor = "pointer";

      if (!tooltipRef.current) return;
      const features = e.features;
      if (!features || features.length === 0) {
        tooltipRef.current.style.display = "none";
        return;
      }

      const props = features[0].properties;
      if (!props) {
        tooltipRef.current.style.display = "none";
        return;
      }

      const county = props.county || "Unknown County";
      const stateFips = (props.geoid || "").substring(0, 2);
      const stateName = STATE_NAMES[stateFips] || "";
      const drs =
        typeof props.drs === "number" ? props.drs.toFixed(1) : "N/A";
      const ebs =
        typeof props.ebs === "number" ? props.ebs.toFixed(1) : "N/A";

      tooltipRef.current.innerHTML = `
        <div style="font-weight:600;font-size:13px;margin-bottom:4px;color:#f3f4f6">${county}${stateName ? ", " + stateName : ""}</div>
        <div style="display:flex;gap:12px;font-size:11px">
          <span style="color:#9ca3af">DRS: <span style="color:${Number(drs) > 50 ? "#f87171" : "#4ade80"};font-weight:600">${drs}</span></span>
          <span style="color:#9ca3af">EBS: <span style="color:${Number(ebs) > 50 ? "#4ade80" : "#f87171"};font-weight:600">${ebs}</span></span>
        </div>
      `;

      tooltipRef.current.style.display = "block";
      tooltipRef.current.style.left = e.point.x + 12 + "px";
      tooltipRef.current.style.top = e.point.y - 12 + "px";
    });

    m.on("mouseleave", "tract-fill", () => {
      m.getCanvas().style.cursor = "";
      if (tooltipRef.current) {
        tooltipRef.current.style.display = "none";
      }
    });

    map.current = m;

    return () => {
      m.remove();
      map.current = null;
      maplibregl.removeProtocol("pmtiles");
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update cursor for placement mode
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    map.current.getCanvas().style.cursor = placing ? "crosshair" : "";
  }, [placing, mapLoaded]);

  // Update metric coloring
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const prop = metric === "drs" ? "drs" : "ebs";
    const colors: [string, string, string, string, string] =
      metric === "drs"
        ? ["#00c800", "#c8c800", "#ffa500", "#ff0000", "#8b0000"]
        : ["#8b0000", "#ff0000", "#ffa500", "#c8c800", "#00c800"];

    map.current.setPaintProperty("tract-fill", "fill-color", [
      "interpolate",
      ["linear"],
      ["get", prop],
      0,
      colors[0],
      25,
      colors[1],
      50,
      colors[2],
      75,
      colors[3],
      100,
      colors[4],
    ]);
  }, [metric, mapLoaded]);

  // Update selected tract highlight
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    map.current.setFilter("tract-highlight", [
      "==",
      "geoid",
      selectedTract?.geoid || "",
    ]);
  }, [selectedTract, mapLoaded]);

  // Update intervention circles
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    if (m.getLayer("intervention-circles")) m.removeLayer("intervention-circles");
    if (m.getLayer("intervention-borders")) m.removeLayer("intervention-borders");
    if (m.getSource("interventions")) m.removeSource("interventions");

    if (interventions.length === 0) return;

    const features = interventions.map((inv) => {
      const center = [inv.location.lng, inv.location.lat];
      const radius = IMPACT_RADII[inv.type] || 1000;
      const points = [];
      for (let i = 0; i < 32; i++) {
        const angle = (i / 32) * 2 * Math.PI;
        const dx = (radius / 111320) * Math.cos(angle);
        const dy = (radius / 110540) * Math.sin(angle);
        points.push([center[0] + dx, center[1] + dy]);
      }
      points.push(points[0]);
      return {
        type: "Feature" as const,
        geometry: { type: "Polygon" as const, coordinates: [points] },
        properties: {
          type: inv.type,
          color: INTERVENTION_COLORS[inv.type] || "#22c55e",
        },
      };
    });

    m.addSource("interventions", {
      type: "geojson",
      data: { type: "FeatureCollection", features },
    });

    m.addLayer({
      id: "intervention-circles",
      type: "fill",
      source: "interventions",
      paint: { "fill-color": ["get", "color"], "fill-opacity": 0.2 },
    });

    m.addLayer({
      id: "intervention-borders",
      type: "line",
      source: "interventions",
      paint: {
        "line-color": ["get", "color"],
        "line-width": 2,
        "line-opacity": 0.8,
      },
    });
  }, [interventions, mapLoaded]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />
      {/* Tooltip overlay */}
      <div
        ref={tooltipRef}
        style={{
          display: "none",
          position: "absolute",
          pointerEvents: "none",
          zIndex: 50,
          backgroundColor: "rgba(17, 24, 39, 0.95)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(55, 65, 81, 0.6)",
          borderRadius: "10px",
          padding: "8px 12px",
          boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
          maxWidth: "240px",
        }}
      />
    </div>
  );
}
