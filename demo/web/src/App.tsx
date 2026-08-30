import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type ChatLine,
  type DialogState,
  type PlaybackPayload,
  type ProductCard,
  type SessionPayload,
  type TurnPayload,
  type UserProfile,
} from "./api";
import ChatPanel from "./components/ChatPanel";
import InternalsPanel from "./components/InternalsPanel";
import ProductGrid from "./components/ProductGrid";
import TopBar from "./components/TopBar";

const PLAY_GAP_MS = 1200;

function sleep(ms: number, signal: { cancelled: boolean }) {
  return new Promise<void>((resolve) => {
    window.setTimeout(() => {
      if (!signal.cancelled) resolve();
    }, ms);
  });
}

function lineId(role: string, turn: number) {
  return `${role}-${turn}-${Math.random().toString(36).slice(2, 7)}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turn, setTurn] = useState(0);
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [targetAsin, setTargetAsin] = useState<string | null>(null);
  const [targetTitle, setTargetTitle] = useState<string | null>(null);
  const [hitRank, setHitRank] = useState<number | null>(null);
  const [hitTurn, setHitTurn] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalogSize, setCatalogSize] = useState<number | null>(null);
  const playLock = useRef({ cancelled: false });

  const applyTurn = useCallback((payload: TurnPayload, appendUser: boolean) => {
    setTurn(payload.turn);
    setProducts(payload.recommendations);
    setDialog(payload.dialog_state);
    setProfile(payload.profile);
    setTargetAsin(payload.target_asin);
    setHitRank(payload.hit_rank);
    setLines((current) => {
      const next = [...current];
      if (appendUser) {
        next.push({
          id: lineId("user", payload.turn),
          role: "user",
          text: payload.user_message,
          turn: payload.turn,
        });
      }
      next.push({
        id: lineId("agent", payload.turn),
        role: "agent",
        text: payload.message,
        askAttribute: payload.ask_attribute,
        turn: payload.turn,
      });
      return next;
    });
  }, []);

  const startSession = useCallback(async () => {
    playLock.current.cancelled = true;
    setPlaying(false);
    setBusy(true);
    setError(null);
    try {
      const session = await api<SessionPayload>("/api/session", {});
      setSessionId(session.session_id);
      setTurn(0);
      setLines([]);
      setProducts([]);
      setDialog(session.dialog_state);
      setProfile(session.profile);
      setTargetAsin(null);
      setTargetTitle(null);
      setHitRank(null);
      setHitTurn(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start session");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void startSession();
    void api<{ catalog_size: number }>("/api/health")
      .then((health) => setCatalogSize(health.catalog_size))
      .catch(() => setCatalogSize(null));
  }, [startSession]);

  async function sendMessage(text: string) {
    if (!sessionId) return;
    setBusy(true);
    setError(null);
    const optimistic: ChatLine = {
      id: lineId("user", turn + 1),
      role: "user",
      text,
      turn: turn + 1,
    };
    setLines((current) => [...current, optimistic]);
    try {
      const payload = await api<TurnPayload>("/api/turn", {
        session_id: sessionId,
        user_message: text,
      });
      applyTurn(payload, false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Turn failed");
    } finally {
      setBusy(false);
    }
  }

  async function playScript(script: "browsing" | "buying" | "replay") {
    playLock.current = { cancelled: false };
    const signal = playLock.current;
    setPlaying(true);
    setBusy(true);
    setError(null);
    setLines([]);
    setProducts([]);
    setHitRank(null);
    setHitTurn(null);
    setTargetAsin(null);
    setTargetTitle(null);
    try {
      const payload = await api<PlaybackPayload>("/api/playback", {
        script,
        sample_id: "public_0001",
      });
      if (signal.cancelled) return;
      setSessionId(payload.session_id);
      setProfile(payload.profile);
      setTargetAsin(payload.target_asin);
      setTargetTitle(payload.target_title);
      for (const step of payload.turns) {
        if (signal.cancelled) return;
        setLines((current) => [
          ...current,
          {
            id: lineId("user", step.turn),
            role: "user",
            text: step.user_message,
            turn: step.turn,
          },
        ]);
        await sleep(450, signal);
        if (signal.cancelled) return;
        applyTurn(step, false);
        if (step.hit_rank != null) {
          setHitRank(step.hit_rank);
          setHitTurn(step.turn);
        }
        await sleep(PLAY_GAP_MS, signal);
      }
      if (!signal.cancelled && payload.hit_rank != null) {
        setHitRank(payload.hit_rank);
        setHitTurn(payload.hit_turn);
      }
    } catch (err) {
      if (!signal.cancelled) {
        setError(err instanceof Error ? err.message : "Playback failed");
      }
    } finally {
      if (!signal.cancelled) {
        setPlaying(false);
        setBusy(false);
      }
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <TopBar
        turn={turn}
        playing={playing}
        catalogSize={catalogSize}
        onNewSession={() => void startSession()}
        onPlay={(script) => void playScript(script)}
      />
      <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(280px,0.9fr)_minmax(420px,1.35fr)_minmax(260px,0.85fr)]">
        <ChatPanel
          lines={lines}
          turn={turn}
          playing={playing}
          busy={busy}
          error={error}
          onSend={(text) => void sendMessage(text)}
        />
        <ProductGrid
          products={products}
          targetAsin={targetAsin}
          targetTitle={targetTitle}
          hitRank={hitRank}
          hitTurn={hitTurn}
        />
        <InternalsPanel dialog={dialog} profile={profile} />
      </main>
    </div>
  );
}
