"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import type { DocumentDetail } from "@/lib/types";

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </h4>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function SensitiveSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-red-200 dark:border-red-900 rounded p-3 space-y-2">
      <h5 className="text-xs font-semibold uppercase text-red-600 dark:text-red-400">
        {title}
      </h5>
      {children}
    </div>
  );
}

function DetailList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <span className="text-xs text-muted-foreground">{label}: </span>
      <span className="text-xs">{items.join(", ")}</span>
    </div>
  );
}

interface DocumentMetadataPanelProps {
  doc: DocumentDetail;
}

export function DocumentMetadataPanel({ doc }: DocumentMetadataPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={`relative transition-all duration-200 ${
        collapsed ? "w-10" : "w-80"
      } shrink-0`}
    >
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-0 left-0 h-8 w-8 z-10"
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? (
          <PanelRightOpen className="h-4 w-4" />
        ) : (
          <PanelRightClose className="h-4 w-4" />
        )}
      </Button>

      {!collapsed && (
        <div className="border rounded p-4 pt-10 space-y-4 overflow-y-auto max-h-[70vh]">
          <h3 className="text-sm font-semibold">Metadata</h3>

          {doc.author && <Section label="Author">{doc.author}</Section>}

          {doc.recipients?.length > 0 && (
            <Section label="Recipients">{doc.recipients.join(", ")}</Section>
          )}

          {doc.keywords?.length > 0 && (
            <Section label="Keywords">
              <div className="flex flex-wrap gap-1">
                {doc.keywords.map((k) => (
                  <Badge key={k} variant="outline" className="text-xs">
                    {k}
                  </Badge>
                ))}
              </div>
            </Section>
          )}

          {doc.people_mentioned?.length > 0 && (
            <Section label="People">{doc.people_mentioned.join(", ")}</Section>
          )}

          {doc.organizations_detail?.length > 0 && (
            <Section label="Organizations">
              <div className="space-y-1">
                {doc.organizations_detail.map((org) => (
                  <div key={org.name} className="text-xs">
                    <span className="font-medium">{org.name}</span>
                    {(org.type || org.country) && (
                      <span className="text-muted-foreground">
                        {" "}
                        ({[org.type, org.country].filter(Boolean).join(", ")})
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {(doc.countries_mentioned?.length > 0 ||
            doc.cities_mentioned?.length > 0 ||
            doc.other_places?.length > 0) && (
            <Section label="Locations">
              <div className="space-y-0.5">
                {doc.countries_mentioned?.length > 0 && (
                  <div className="text-xs">{doc.countries_mentioned.join(", ")}</div>
                )}
                {doc.cities_mentioned?.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {doc.cities_mentioned.join(", ")}
                  </div>
                )}
                {doc.other_places?.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {doc.other_places.join(", ")}
                  </div>
                )}
              </div>
            </Section>
          )}

          {doc.document_description && (
            <Section label="Description">{doc.document_description}</Section>
          )}

          {doc.date_range && (doc.date_range.start_date || doc.date_range.end_date) && (
            <Section label="Date Range">
              <span className="text-xs">
                {doc.date_range.start_date} to {doc.date_range.end_date}
                {doc.date_range.is_approximate && " (approximate)"}
              </span>
            </Section>
          )}

          {doc.declassification_date && (
            <Section label="Declassification Date">
              {doc.declassification_date}
            </Section>
          )}

          {doc.archive_location && (
            <Section label="Archive Location">{doc.archive_location}</Section>
          )}

          {doc.observations && (
            <Section label="Observations">{doc.observations}</Section>
          )}

          {doc.concerns?.length > 0 && (
            <Section label="Concerns">
              <div className="flex flex-wrap gap-1">
                {doc.concerns.map((c, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {c}
                  </Badge>
                ))}
              </div>
            </Section>
          )}

          {/* Sensitive content sections */}
          {doc.financial_references?.has_financial_content && (
            <SensitiveSection title="Financial Content">
              {doc.financial_references.amounts?.length > 0 && (
                <div className="space-y-1">
                  {doc.financial_references.amounts.map((a, i) => (
                    <div key={i} className="text-xs">
                      <span className="font-medium">{a.value}</span>
                      {a.normalized_usd != null && (
                        <span className="text-muted-foreground">
                          {" "}
                          (${a.normalized_usd.toLocaleString()} USD)
                        </span>
                      )}
                      {a.context && (
                        <span className="text-muted-foreground"> &mdash; {a.context}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <DetailList label="Actors" items={doc.financial_references.financial_actors ?? []} />
              <DetailList label="Purposes" items={doc.financial_references.purposes ?? []} />
            </SensitiveSection>
          )}

          {doc.violence_references?.has_violence_content && (
            <SensitiveSection title="Violence">
              <DetailList label="Types" items={doc.violence_references.incident_types ?? []} />
              <DetailList label="Victims" items={doc.violence_references.victims ?? []} />
              <DetailList label="Perpetrators" items={doc.violence_references.perpetrators ?? []} />
            </SensitiveSection>
          )}

          {doc.torture_references?.has_torture_content && (
            <SensitiveSection title="Torture">
              <DetailList
                label="Detention Centers"
                items={doc.torture_references.detention_centers ?? []}
              />
              <DetailList label="Victims" items={doc.torture_references.victims ?? []} />
              <DetailList label="Perpetrators" items={doc.torture_references.perpetrators ?? []} />
              <DetailList label="Methods" items={doc.torture_references.methods_mentioned ?? []} />
            </SensitiveSection>
          )}

          {doc.disappearance_references?.has_disappearance_content && (
            <SensitiveSection title="Disappearances">
              <DetailList label="Victims" items={doc.disappearance_references.victims ?? []} />
              <DetailList
                label="Perpetrators"
                items={doc.disappearance_references.perpetrators ?? []}
              />
              <DetailList label="Locations" items={doc.disappearance_references.locations ?? []} />
              <DetailList
                label="Dates"
                items={doc.disappearance_references.dates_mentioned ?? []}
              />
            </SensitiveSection>
          )}
        </div>
      )}
    </div>
  );
}
