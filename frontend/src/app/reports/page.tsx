"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchReports } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  answered: "bg-green-100 text-green-800",
  partially_answered: "bg-yellow-100 text-yellow-800",
  unanswered: "bg-gray-100 text-gray-800",
  needs_more_data: "bg-red-100 text-red-800",
};

export default function ReportsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  if (isLoading) {
    return (
      <div className="container py-8 space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Research Questions</h1>
      <div className="space-y-4">
        {data?.items.map((rq) => (
          <Link key={rq.id} href={`/reports/${rq.id}`}>
            <Card className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{rq.id}</Badge>
                  <Badge className={STATUS_COLORS[rq.status] ?? ""} variant="secondary">
                    {rq.status.replace("_", " ")}
                  </Badge>
                  <Badge variant="secondary">{rq.category}</Badge>
                </div>
                <CardTitle className="text-base mt-2">{rq.question}</CardTitle>
              </CardHeader>
              {rq.rag_results && (
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3">{rq.rag_results}</p>
                </CardContent>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
