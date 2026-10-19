/** Resolves a public asset against Vite's deployment base. */
export function assetUrl(path: string, base = import.meta.env.BASE_URL): string {
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  return `${normalizedBase}${path.replace(/^\/+/, "")}`;
}
