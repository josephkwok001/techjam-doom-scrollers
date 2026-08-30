/**
 * Demo-only display parsing for agent slot values.
 * Mirrors ATTRIBUTE_TERMS in starter/agent.py — does not change the scored agent.
 */

const GENERIC_CATEGORY = new Set(["looking for", "need", "want"]);
const GENERIC_MATERIAL = new Set(["material"]);
const GENERIC_COLOR = new Set(["color"]);
const GENERIC_FEATURE = new Set(["feature"]);
const GENERIC_STYLE = new Set(["style"]);
const GENERIC_SIZE = new Set(["size"]);

const ATTRIBUTE_TERMS: Record<string, readonly string[]> = {
  category: ["looking for", "need", "want", "shoes", "dress", "shirt", "bag", "jewelry", "boots"],
  material: ["leather", "cotton", "wool", "linen", "suede", "silk", "denim", "material"],
  color: ["black", "white", "blue", "red", "green", "brown", "pink", "grey", "gray", "color"],
  size: ["size", "small", "medium", "large", " xs ", " s ", " m ", " l ", " xl "],
  style: ["style", "casual", "formal", "vintage", "minimalist", "classic", "sporty"],
  brand: ["brand"],
  budget: ["$", "budget", "under", "less than", "cheap", "affordable", "price"],
  feature: ["feature", "waterproof", "comfortable", "durable", "pockets", "slip resistant"],
  use_case: ["for work", "for running", "for hiking", "for a wedding", "for travel", "gift", "occasion"],
};

const GENERIC_BY_ATTRIBUTE: Record<string, Set<string>> = {
  category: GENERIC_CATEGORY,
  material: GENERIC_MATERIAL,
  color: GENERIC_COLOR,
  feature: GENERIC_FEATURE,
  style: GENERIC_STYLE,
  size: GENERIC_SIZE,
};

const BUDGET_RE =
  /budget\s+around\s*\$?\s*[\d.]+|under\s+\$?\s*[\d.]+|less\s+than\s+\$?\s*[\d.]+|\$\s*[\d.]+/i;

function findMatches(raw: string, terms: readonly string[]): string[] {
  const lowered = ` ${raw.toLowerCase()} `;
  const found: string[] = [];
  for (const term of terms) {
    if (lowered.includes(term.toLowerCase()) && !found.includes(term.trim())) {
      found.push(term.trim());
    }
  }
  return found;
}

/** Short label for the How it works panel; falls back to full raw text. */
export function formatSlotDisplay(attribute: string, raw: string | null): string {
  if (!raw) return "—";

  if (attribute === "budget") {
    const match = raw.match(BUDGET_RE);
    if (match) return match[0].replace(/\s+/g, " ").trim();
  }

  const terms = ATTRIBUTE_TERMS[attribute];
  if (!terms) return raw;

  let matches = findMatches(raw, terms);
  const generics = GENERIC_BY_ATTRIBUTE[attribute];
  if (generics) {
    const concrete = matches.filter((term) => !generics.has(term));
    if (concrete.length > 0) matches = concrete;
  }

  if (matches.length > 0) {
    return [...new Set(matches)].join(", ");
  }

  return raw;
}
