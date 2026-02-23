import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function AboutPage() {
  return (
    <div className="container max-w-3xl py-8 space-y-8">
      <h1 className="text-3xl font-bold">About This Project</h1>
      <p className="text-muted-foreground">
        This project processes and makes accessible approximately 21,000 declassified CIA
        documents related to the Chilean dictatorship (1973-1990), released by the US government
        as part of its declassification program.
      </p>

      <Separator />

      <section>
        <h2 className="text-xl font-semibold mb-4">The Problem</h2>
        <p className="text-sm mb-4">
          While the US government declassified these documents, the sheer volume makes them
          practically inaccessible for researchers, journalists, and the general public.
          This project creates a searchable, structured database with AI-powered transcription
          and analysis to enable meaningful research at scale.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Methodology</h2>
        <div className="grid gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">1. PDF Transcription</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Each PDF is processed using OpenAI vision models that extract text and structured
              metadata (dates, people, organizations, classification levels, keywords).
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">2. Vector Indexing</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Transcribed documents are chunked and embedded into a vector database (ChromaDB)
              for semantic search and retrieval.
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">3. Analysis & Visualization</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Metadata is aggregated to produce timelines, entity networks, geographic maps,
              and thematic analysis across the entire corpus.
            </CardContent>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Limitations</h2>
        <ul className="list-disc pl-6 text-sm space-y-2 text-muted-foreground">
          <li>Not all documents have been transcribed yet. Coverage is ongoing.</li>
          <li>AI transcription may contain errors, especially with handwritten or degraded documents.</li>
          <li>Metadata extraction is automated and may misidentify entities or dates.</li>
          <li>This is a research tool, not a definitive historical record.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Open Source</h2>
        <p className="text-sm text-muted-foreground">
          This project is open source. The code, methodology, and documentation are publicly
          available for review and contribution.
        </p>
      </section>
    </div>
  );
}
