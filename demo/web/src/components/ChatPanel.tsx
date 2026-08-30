import { useEffect, useRef, type FormEvent } from "react";
import type { ChatLine } from "../api";

type Props = {
  lines: ChatLine[];
  turn: number;
  playing: boolean;
  busy: boolean;
  error: string | null;
  onSend: (text: string) => void;
};

export default function ChatPanel({ lines, turn, playing, busy, error, onSend }: Props) {
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines, busy]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = input.current?.value.trim() ?? "";
    if (!value || busy || playing || turn >= 10) return;
    onSend(value);
    if (input.current) input.current.value = "";
  }

  return (
    <section className="flex min-h-0 flex-col border-r border-white/8 bg-[#181410]">
      <div className="border-b border-white/8 px-4 py-3">
        <h2 className="text-sm font-semibold text-[#f4efe6]">Shop assistant</h2>
        <p className="text-xs text-[#b9a894]">Offline BM25 · no LLM calls</p>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {lines.length === 0 && (
          <div className="rounded-xl border border-dashed border-white/12 p-4 text-sm leading-relaxed text-[#b9a894]">
            Ask for an item, or play a scripted demo. The agent narrows 50,000 catalog
            products turn by turn and always asks a clarifying question.
          </div>
        )}
        {lines.map((line) => (
          <div
            key={line.id}
            className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
              line.role === "user"
                ? "ml-auto bg-[#e8c27a] text-[#1b1713]"
                : "bg-[#2a241e] text-[#f4efe6]"
            }`}
          >
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-70">
              {line.role === "user" ? "You" : "Agent"} · turn {line.turn}
            </p>
            <p>{line.text}</p>
            {line.role === "agent" && line.askAttribute && (
              <p className="mt-2 inline-flex rounded-full bg-[#e8c27a]/15 px-2 py-0.5 text-[11px] font-medium text-[#e8c27a]">
                Asking: {line.askAttribute}
              </p>
            )}
          </div>
        ))}
        {busy && (
          <p className="text-xs text-[#b9a894]">{playing ? "Playing demo…" : "Searching catalog…"}</p>
        )}
        <div ref={bottom} />
      </div>

      {error && <p className="px-4 pb-2 text-xs text-[#e07a6e]">{error}</p>}

      <form onSubmit={handleSubmit} className="border-t border-white/8 p-3">
        <div className="flex gap-2">
          <input
            ref={input}
            disabled={busy || playing || turn >= 10}
            placeholder={turn >= 10 ? "Session complete" : "Describe what you want…"}
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-[#241f1a] px-3 py-2.5 text-sm text-[#f4efe6] outline-none placeholder:text-[#7d7164] focus:border-[#e8c27a]/50"
          />
          <button
            type="submit"
            disabled={busy || playing || turn >= 10}
            className="rounded-xl bg-[#e8c27a] px-4 text-sm font-semibold text-[#1b1713] disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
