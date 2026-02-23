"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ClassificationChart } from "@/components/charts/classification-chart";
import { TimelineChart } from "@/components/charts/timeline-chart";
import { useStats } from "@/hooks/useStats";

export default function DashboardPage() {
  const { data: stats, isLoading } = useStats();

  if (isLoading || !stats) {
    return (
      <div className="container py-8 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  const progress = stats.transcription_progress;

  return (
    <div className="container py-8 space-y-8">
      <h1 className="text-3xl font-bold">
        Declassified CIA Documents on Chile
      </h1>
      <p className="text-muted-foreground">
        Exploring {stats.total_documents.toLocaleString()} transcribed documents
        ({stats.total_pages.toLocaleString()} pages) from the US declassification
        program on the Chilean dictatorship (1973-1990).
      </p>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Documents" value={stats.total_documents.toLocaleString()} subtitle={`${stats.total_pages.toLocaleString()} pages`} />
        <StatCard
          title="Transcription"
          value={`${Math.round((progress.completed / progress.total) * 100)}%`}
          subtitle={`${progress.completed.toLocaleString()} / ${progress.total.toLocaleString()}`}
        />
        <StatCard title="Avg Confidence" value={`${(stats.avg_confidence * 100).toFixed(1)}%`} subtitle="across all transcripts" />
        <StatCard
          title="Sensitive Content"
          value={stats.sensitive_content.violence.toLocaleString()}
          subtitle={`violence refs | ${stats.sensitive_content.torture.toLocaleString()} torture | ${stats.sensitive_content.disappearances.toLocaleString()} disappearances`}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Documents Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <TimelineChart data={stats.timeline} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Classification Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ClassificationChart data={stats.classification_distribution} />
          </CardContent>
        </Card>
      </div>

      {/* Top entities */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <EntityList title="Top People" items={stats.top_people} href="/entities?type=person" />
        <EntityList title="Top Organizations" items={stats.top_organizations} href="/entities?type=organization" />
        <EntityList title="Top Keywords" items={stats.top_keywords} href="/entities?type=keyword" />
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function EntityList({ title, items, href }: { title: string; items: { name: string; count: number }[]; href: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.slice(0, 10).map((item) => (
            <li key={item.name} className="flex justify-between text-sm">
              <span className="truncate">{item.name}</span>
              <span className="text-muted-foreground ml-2">{item.count.toLocaleString()}</span>
            </li>
          ))}
        </ul>
        <Link href={href} className="text-sm text-blue-600 hover:underline mt-4 inline-block">
          View all &rarr;
        </Link>
      </CardContent>
    </Card>
  );
}
