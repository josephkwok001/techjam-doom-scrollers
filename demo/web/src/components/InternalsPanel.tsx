import type { DialogState, UserProfile } from "../api";
import { formatSlotDisplay } from "../slotDisplay";

const ATTRIBUTES = [
  "category",
  "material",
  "color",
  "size",
  "style",
  "brand",
  "budget",
  "feature",
  "use_case",
];

function statusStyle(status: string): string {
  if (status === "confirmed") return "bg-[#7dce9a] text-[#102016]";
  if (status === "unconstrained") return "bg-[#e8c27a]/20 text-[#e8c27a]";
  return "bg-white/8 text-[#b9a894]";
}

type Props = {
  dialog: DialogState | null;
  profile: UserProfile | null;
};

export default function InternalsPanel({ dialog, profile }: Props) {
  const tags = profile?.preference_tags ?? [];
  const buying = dialog?.intent === "buying";

  return (
    <aside className="flex min-h-0 flex-col overflow-y-auto border-l border-white/8 bg-[#181410] px-4 py-4">
      <h2 className="text-sm font-semibold text-[#f4efe6]">How it works</h2>
      <p className="mt-1 text-xs text-[#b9a894]">Live state, updated every turn</p>

      <section className="mt-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8a7d70]">
          Intent
        </p>
        <span
          className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
            buying
              ? "bg-[#8b3a32]/80 text-[#f8e4e1]"
              : "bg-[#3d5c4a] text-[#e4f0e8]"
          }`}
        >
          {buying ? "Buying" : "Browsing"}
        </span>
        <p className="mt-1.5 text-xs leading-snug text-[#8a7d70]">
          {buying
            ? "Narrowing to stated requirements"
            : "Still exploring, keeping options open"}
        </p>
      </section>

      <section className="mt-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8a7d70]">
          What the shopper has told us
        </p>
        <ul className="mt-2 space-y-1.5">
          {ATTRIBUTES.map((attribute) => {
            const status = dialog?.slot_status[attribute] ?? "unknown";
            const value = dialog?.slots[attribute] ?? null;
            return (
              <li key={attribute} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 shrink-0 rounded-full px-1.5 py-0.5 capitalize ${statusStyle(status)}`}>
                  {status === "confirmed" ? "set" : status === "unconstrained" ? "any" : "—"}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="font-medium capitalize text-[#f4efe6]">
                    {attribute.replace("_", " ")}
                  </span>
                  <span className="block break-words whitespace-normal leading-snug text-[#8a7d70]">
                    {formatSlotDisplay(attribute, value)}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="mt-5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8a7d70]">
          Shopper profile
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {tags.length === 0 && <span className="text-xs text-[#8a7d70]">No tags</span>}
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-[#e8c27a]/25 bg-[#e8c27a]/10 px-2 py-0.5 text-[11px] text-[#e8c27a]"
            >
              {tag}
            </span>
          ))}
        </div>
        <p className="mt-2 text-xs text-[#b9a894]">{profile?.rating_style ?? "—"}</p>
      </section>
    </aside>
  );
}
