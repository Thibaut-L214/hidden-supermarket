// Content schema (docs/CONTENT_SCHEMA.md). No fact without a source; unknowns are TODO_SOURCE.

export const TODO_SOURCE = "TODO_SOURCE";

export interface SourceRef {
  id: string;
  label: string;
  url: string;
  publisher: string;
  /** ISO date of consultation. */
  consultedAt: string;
}

export interface Caption {
  id: string;
  title: string;
  /** One idea, at most 140 characters, shown in the immersive view. */
  short: string;
  /** On-demand panel text. */
  detail: string;
  /** "schematic" = illustration; "verified" = field statement that needs a source. */
  kind: "schematic" | "verified";
  source?: SourceRef | typeof TODO_SOURCE;
  /** Geographic scale and period, e.g. « France, 2024 ». */
  scope: string;
  status: "draft" | "review" | "validated";
}

export const SHORT_MAX = 140;
