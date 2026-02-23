import { Badge } from "@/components/ui/badge";

const COLORS: Record<string, string> = {
  "TOP SECRET": "bg-red-600 text-white hover:bg-red-600",
  SECRET: "bg-orange-500 text-white hover:bg-orange-500",
  CONFIDENTIAL: "bg-yellow-500 text-black hover:bg-yellow-500",
  UNCLASSIFIED: "bg-green-600 text-white hover:bg-green-600",
};

export function ClassificationBadge({
  level,
}: {
  level: string;
}) {
  return (
    <Badge className={COLORS[level] ?? "bg-gray-500 text-white"}>
      {level}
    </Badge>
  );
}
