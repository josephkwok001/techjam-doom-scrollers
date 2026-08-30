export type ProductCard = {
  parent_asin: string;
  rank: number;
  title: string;
  store: string;
  price: number | null;
  average_rating: number | null;
  rating_number: number | null;
  categories: string;
  is_target: boolean;
};

export type DialogState = {
  intent: string;
  slots: Record<string, string | null>;
  slot_status: Record<string, string>;
  unconstrained: string[];
  asked: string[];
  history: string[];
  retrieval_feedback: {
    candidate_count?: number;
    overloaded?: boolean;
    missing_attributes?: string[];
    relaxed_search?: boolean;
  };
};

export type UserProfile = {
  preference_tags?: string[];
  rating_style?: string;
  summary?: string;
  purchase_frequency?: string;
  average_prior_rating?: number | null;
};

export type TurnPayload = {
  session_id: string;
  turn: number;
  user_message: string;
  message: string;
  ask_attribute: string | null;
  recommendations: ProductCard[];
  dialog_state: DialogState;
  profile: UserProfile;
  usage: { prompt_tokens: number; completion_tokens: number };
  target_asin: string | null;
  hit_rank: number | null;
};

export type SessionPayload = {
  session_id: string;
  turn: number;
  profile: UserProfile;
  dialog_state: DialogState;
  recommendations: ProductCard[];
  message: string;
  ask_attribute: string | null;
  target_asin: string | null;
  hit_rank: number | null;
};

export type PlaybackPayload = {
  session_id: string;
  script: string;
  sample_id: string | null;
  scenario_type: string;
  target_asin: string | null;
  target_title: string | null;
  hit_turn: number | null;
  hit_rank: number | null;
  profile: UserProfile;
  turns: TurnPayload[];
};

export type ChatLine = {
  id: string;
  role: "user" | "agent";
  text: string;
  askAttribute?: string | null;
  turn: number;
};

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}
