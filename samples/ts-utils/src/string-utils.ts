export function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1);
}
export function truncate(s: string, maxLen: number): string {
  return s.length <= maxLen ? s : s.slice(0, maxLen - 1) + "…";
}
export function slugify(s: string): string {
  return s.toLowerCase().replace(/\s+/g, "-").replace(/[^\w-]/g, "");
}
