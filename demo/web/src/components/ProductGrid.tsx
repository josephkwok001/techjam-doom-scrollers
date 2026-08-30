import type { ProductCard } from "../api";

const TILES = [
  "from-[#5c4030] to-[#2a1f18]",
  "from-[#3d4f3a] to-[#1c241b]",
  "from-[#3a4558] to-[#1b2028]",
  "from-[#5a3a42] to-[#27181c]",
  "from-[#4a4330] to-[#242015]",
  "from-[#3d3a52] to-[#1c1b26]",
];

function tileClass(categories: string): string {
  let hash = 0;
  for (let i = 0; i < categories.length; i += 1) {
    hash = (hash + categories.charCodeAt(i)) % TILES.length;
  }
  return TILES[hash] ?? TILES[0];
}

function formatPrice(price: number | null): string {
  if (price == null) return "—";
  return `$${price.toFixed(2)}`;
}

type Props = {
  products: ProductCard[];
  targetAsin: string | null;
  targetTitle: string | null;
  hitRank: number | null;
  hitTurn: number | null;
};

export default function ProductGrid({
  products,
  targetAsin,
  targetTitle,
  hitRank,
  hitTurn,
}: Props) {
  return (
    <section className="flex min-h-0 flex-col bg-[#14110e]">
      <div className="flex items-start justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-[#f4efe6]">Top 10 recommendations</h2>
          <p className="text-xs text-[#b9a894]">Ranked each turn from the in-memory FTS5 index</p>
        </div>
        {targetAsin && (
          <div className="max-w-[55%] rounded-lg border border-[#7dce9a]/30 bg-[#7dce9a]/10 px-2.5 py-1.5 text-right">
            <p className="text-[10px] uppercase tracking-wider text-[#7dce9a]">
              {hitRank != null ? `Target found · rank ${hitRank}${hitTurn != null ? ` · turn ${hitTurn}` : ""}` : "Replay target"}
            </p>
            <p className="truncate text-xs text-[#f4efe6]">{targetTitle ?? targetAsin}</p>
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {products.length === 0 ? (
          <div className="flex h-full min-h-[240px] items-center justify-center rounded-2xl border border-dashed border-white/12 px-6 text-center text-sm leading-relaxed text-[#b9a894]">
            Offline agent over 50,000 Amazon-derived products. No images in the catalog —
            cards show title, store, price, and rating. Send a message or play a demo to
            fill this shelf.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-2">
            {products.map((product) => (
              <article
                key={`${product.parent_asin}-${product.rank}`}
                className={`overflow-hidden rounded-2xl border bg-[#1e1a16] ${
                  product.is_target
                    ? "border-[#7dce9a] ring-2 ring-[#7dce9a]/40"
                    : product.rank === 1
                      ? "border-[#e8c27a]/50"
                      : "border-white/8"
                }`}
              >
                <div
                  className={`relative flex h-16 items-end bg-gradient-to-br ${tileClass(product.categories)} px-3 py-2`}
                >
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                      product.rank === 1
                        ? "bg-[#e8c27a] text-[#1b1713]"
                        : "bg-black/40 text-[#f4efe6]"
                    }`}
                  >
                    {product.rank}
                  </span>
                  {product.is_target && (
                    <span className="ml-auto rounded-full bg-[#7dce9a] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#102016]">
                      Target
                    </span>
                  )}
                </div>
                <div className="space-y-1.5 p-3">
                  <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-[#f4efe6]">
                    {product.title}
                  </h3>
                  <p className="truncate text-xs text-[#b9a894]">{product.store || "Unknown store"}</p>
                  <p className="line-clamp-1 text-[11px] text-[#8a7d70]">{product.categories}</p>
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <span className="font-semibold text-[#e8c27a]">{formatPrice(product.price)}</span>
                    <span className="text-[#b9a894]">
                      {product.average_rating != null ? `${product.average_rating.toFixed(1)}★` : "No rating"}
                      {product.rating_number != null ? ` · ${product.rating_number.toLocaleString()}` : ""}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
