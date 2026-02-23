import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClassificationBadge } from "./classification-badge";
import type { DocumentListItem } from "@/lib/types";

export function DocumentCard({
  doc,
  onClick,
}: {
  doc: DocumentListItem;
  onClick: () => void;
}) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">{doc.date}</span>
          <ClassificationBadge level={doc.classification} />
          <Badge variant="outline">{doc.type}</Badge>
        </div>
        <h3 className="font-medium text-sm line-clamp-2">{doc.title || `Document ${doc.id}`}</h3>
        <p className="text-xs text-muted-foreground line-clamp-2">{doc.summary}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{doc.pages} {doc.pages === 1 ? "page" : "pages"}</span>
          <span>ID: {doc.id}</span>
        </div>
      </CardContent>
    </Card>
  );
}
