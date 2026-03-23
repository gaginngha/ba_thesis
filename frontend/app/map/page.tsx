"use client";

export default function MapPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Map Explorer</h1>
      <p className="text-gray-600">
        Interactive choropleth map of Swiss municipalities. Select a metric to visualize across all municipalities.
      </p>

      {/* Placeholder for MapLibre GL integration */}
      <div className="bg-white rounded-lg border p-8 text-center min-h-[500px] flex items-center justify-center">
        <div className="text-gray-400">
          <p className="text-lg font-medium mb-2">Map visualization</p>
          <p className="text-sm">
            Requires municipality GeoJSON boundaries from swisstopo.
            <br />
            Integration with MapLibre GL JS will render choropleth maps
            <br />
            showing selected metrics across all ~2,131 municipalities.
          </p>
        </div>
      </div>
    </div>
  );
}
