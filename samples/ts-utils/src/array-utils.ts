import { capitalize } from "./string-utils";
export function unique<T>(arr: T[]): T[] {
  return [...new Set(arr)];
}
export function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}
export function capitalizeAll(arr: string[]): string[] {
  return arr.map(capitalize);
}
