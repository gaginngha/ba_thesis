interface ScoreCardProps {
  label: string;
  value: number | null;
  rank?: number | null;
}

export function ScoreCard({ label, value, rank }: ScoreCardProps) {
  let bgColor = "bg-gray-100";
  let textColor = "text-gray-700";

  if (value !== null) {
    if (value >= 75) {
      bgColor = "bg-green-50 border-green-200";
      textColor = "text-green-700";
    } else if (value >= 50) {
      bgColor = "bg-yellow-50 border-yellow-200";
      textColor = "text-yellow-700";
    } else if (value >= 25) {
      bgColor = "bg-orange-50 border-orange-200";
      textColor = "text-orange-700";
    } else {
      bgColor = "bg-red-50 border-red-200";
      textColor = "text-red-700";
    }
  }

  return (
    <div className={`rounded-lg border p-4 ${bgColor}`}>
      <div className="text-sm text-gray-600">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${textColor}`}>
        {value !== null ? value.toFixed(1) : "—"}
      </div>
      {rank && (
        <div className="text-xs text-gray-500 mt-1">
          Rank #{rank}
        </div>
      )}
    </div>
  );
}
