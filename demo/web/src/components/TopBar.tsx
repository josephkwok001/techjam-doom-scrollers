type Props = {
  turn: number;
  playing: boolean;
  catalogSize: number | null;
  onNewSession: () => void;
  onPlay: (script: "browsing" | "buying" | "replay") => void;
};

export default function TopBar({ turn, playing, catalogSize, onNewSession, onPlay }: Props) {
  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-white/8 bg-[#1b1713] px-5 py-3">
      <div className="mr-2 min-w-0">
        <p className="font-display text-lg font-semibold tracking-tight text-[#f4efe6]">
          Doom Scrollers
        </p>
        <p className="text-[11px] uppercase tracking-[0.16em] text-[#b9a894]">
          Conversational e-commerce search
        </p>
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        <span className="text-xs text-[#b9a894]">
          Turn {turn}/10
          {catalogSize != null ? ` · ${catalogSize.toLocaleString()} products` : ""}
        </span>
        <button
          type="button"
          disabled={playing}
          onClick={onNewSession}
          className="rounded-lg border border-white/12 px-3 py-1.5 text-sm text-[#f4efe6] hover:bg-white/6 disabled:opacity-40"
        >
          New session
        </button>
        <button
          type="button"
          disabled={playing}
          onClick={() => onPlay("browsing")}
          className="rounded-lg bg-[#e8c27a] px-3 py-1.5 text-sm font-semibold text-[#1b1713] hover:bg-[#f0d39a] disabled:opacity-40"
        >
          Play browsing
        </button>
        <button
          type="button"
          disabled={playing}
          onClick={() => onPlay("buying")}
          className="rounded-lg bg-[#3d5c4a] px-3 py-1.5 text-sm font-semibold text-[#e4f0e8] hover:bg-[#4a6e59] disabled:opacity-40"
        >
          Play buying
        </button>
        <button
          type="button"
          disabled={playing}
          onClick={() => onPlay("replay")}
          className="rounded-lg bg-[#8b3a32] px-3 py-1.5 text-sm font-semibold text-[#f8e4e1] hover:bg-[#a3483e] disabled:opacity-40"
        >
          Replay hit
        </button>
      </div>
    </header>
  );
}
