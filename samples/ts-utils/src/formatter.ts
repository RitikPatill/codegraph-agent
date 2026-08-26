import { capitalize, truncate } from "./string-utils";
import { unique } from "./array-utils";

export class Formatter {
  private maxLen: number;
  constructor(maxLen = 80) { this.maxLen = maxLen; }
  format(items: string[]): string[] {
    return items.map((s) => truncate(capitalize(s), this.maxLen));
  }
  formatUnique(items: string[]): string[] {
    return this.format(unique(items));
  }
}
