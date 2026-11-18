export interface Segment {
  text: string;
  hit: boolean;
}

/**
 * Splits a snippet so the words the index matched can be marked.
 * `terms` are the index terms the backend reports for a hit: lower-case words.
 */
export function splitHighlight(text: string, terms: readonly string[]): Segment[] {
  const wanted = new Set(terms);
  if (wanted.size === 0) return text ? [{ text, hit: false }] : [];

  const segments: Segment[] = [];
  for (const part of text.split(/([A-Za-z0-9]+)/)) {
    if (!part) continue;
    const hit = wanted.has(part.toLowerCase());
    const last = segments[segments.length - 1];
    if (last && last.hit === hit && !hit) last.text += part;
    else segments.push({ text: part, hit });
  }
  return segments;
}
