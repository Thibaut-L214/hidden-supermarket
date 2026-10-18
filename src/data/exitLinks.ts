// End menu links (docs/GDD.md §09, docs/TECH.md §08). Only official L214 domains; every link is
// to be confirmed before publication. Unknown addresses stay null and are shown as pending,
// never guessed.
export interface ExitLink {
  label: string;
  url: string | null;
}

export const EXIT_LINKS: readonly ExitLink[] = [
  // Address given in docs/TECH.md §11, still to be confirmed.
  { label: "Découvrir L214", url: "https://www.l214.com/" },
  { label: "Lire les enquêtes", url: null },
  { label: "Agir", url: null },
  { label: "Faire un don", url: null },
];

export const OFFICIAL_HOSTS = ["l214.com", "www.l214.com"] as const;
