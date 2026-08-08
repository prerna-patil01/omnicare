import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, AlertTriangle, Brain, Check, Droplet, Heart, Leaf, Plus, Send, Shield, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import * as omni from "@/services/omniService";
import { Badge, Button, Card, ErrorNote, Eyebrow, Skeleton } from "@/components/ui";

const ICONS = { heart: Heart, activity: Activity, brain: Brain, droplet: Droplet, shield: Shield, leaf: Leaf };
const STANCE = {
  concur: { tone: "sage", label: "Concurs" },
  dissent: { tone: "rose", label: "Dissents" },
  abstain: { tone: "neutral", label: "Abstains" },
};

export default function AskOmni() {
  const [conversations, setConversations] = useState([]);
  const [access, setAccess] = useState(null);
  const [engine, setEngine] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const feedRef = useRef(null);

  const loadList = useCallback(async () => {
    try {
      const data = await omni.fetchConversations();
      setConversations(data.conversations);
      setAccess(data.access);
      setEngine(data.engine);
      return data.conversations;
    } catch (err) {
      setError(err.message);
      return [];
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const list = await loadList();
      if (cancelled) return;
      if (list.length) setActiveId(list[0].id);
      else {
        try {
          const { conversation } = await omni.createConversation();
          if (!cancelled) {
            setConversations([conversation]);
            setActiveId(conversation.id);
          }
        } catch (err) {
          if (!cancelled) setError(err.message);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadList]);

  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    omni
      .fetchConversation(activeId)
      .then((data) => !cancelled && setMessages(data.messages))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  // Keep the newest turn in view as the feed grows.
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function handleSend(event) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || sending || !activeId) return;

    setSending(true);
    setDraft("");
    try {
      const data = await omni.sendMessage(activeId, body);
      setMessages((prev) => [...prev, ...data.messages]);
      loadList();
    } catch (err) {
      toast.error(err.message);
      setDraft(body);
    } finally {
      setSending(false);
    }
  }

  async function handleNew() {
    try {
      const { conversation } = await omni.createConversation();
      setConversations((prev) => [conversation, ...prev]);
      setActiveId(conversation.id);
      setMessages([]);
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await omni.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeId === id) {
        setActiveId(remaining[0]?.id ?? null);
        setMessages([]);
      }
    } catch (err) {
      toast.error(err.message);
    }
  }

  if (error && !conversations.length) return <ErrorNote message={error} onRetry={loadList} />;

  return (
    <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
      <aside className="flex flex-col gap-4">
        <Button variant="outline" onClick={handleNew} className="w-full">
          <Plus size={16} /> New conversation
        </Button>

        <Card className="flex flex-col gap-1 p-2">
          {conversations.length === 0 && (
            <p className="px-3 py-4 text-sm" style={{ color: "var(--ink-faint)" }}>
              No conversations yet.
            </p>
          )}
          {conversations.map((convo) => (
            <div key={convo.id} className="group flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveId(convo.id)}
                className="flex-1 truncate rounded-xl px-3 py-2.5 text-left text-sm"
                style={{
                  backgroundColor: convo.id === activeId ? "var(--primary-wash)" : "transparent",
                  color: convo.id === activeId ? "var(--primary)" : "var(--ink-muted)",
                  fontWeight: convo.id === activeId ? 600 : 400,
                }}
              >
                {convo.title}
              </button>
              <button
                type="button"
                onClick={() => handleDelete(convo.id)}
                aria-label={`Delete ${convo.title}`}
                className="rounded-lg p-1.5 opacity-0 transition-opacity group-hover:opacity-100"
                style={{ color: "var(--ink-faint)" }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </Card>

        {access && (
          <Card className="p-4">
            <Eyebrow>What Omni can read</Eyebrow>
            <ul className="mt-2.5 flex flex-col gap-1.5 text-sm">
              {access.canRead.map((scope) => (
                <li key={scope} className="flex items-start gap-2" style={{ color: "var(--ink-muted)" }}>
                  <Check size={14} className="mt-0.5 shrink-0" style={{ color: "var(--sage)" }} />
                  {scope}
                </li>
              ))}
              {access.cannotRead.map((scope) => (
                <li
                  key={scope}
                  className="flex items-start gap-2 line-through"
                  style={{ color: "var(--ink-faint)" }}
                >
                  <span className="mt-1.5 h-px w-3 shrink-0" style={{ backgroundColor: "var(--ink-faint)" }} />
                  {scope}
                </li>
              ))}
            </ul>
            {engine && (
              <p className="mt-3 text-xs" style={{ color: "var(--ink-faint)" }}>
                Reasoning engine: {engine}
              </p>
            )}
          </Card>
        )}
      </aside>

      <Card className="flex h-[calc(100vh-13rem)] min-h-[520px] flex-col overflow-hidden">
        <div ref={feedRef} className="flex-1 overflow-y-auto p-5 sm:p-7">
          {messages.length === 0 && !sending && <Opener />}
          <div className="flex flex-col gap-5">
            {messages.map((message) =>
              message.role === "user" ? (
                <UserBubble key={message.id} message={message} />
              ) : (
                <OmniReply key={message.id} message={message} />
              ),
            )}
            {sending && <Thinking />}
          </div>
        </div>

        <form
          onSubmit={handleSend}
          className="flex items-center gap-2 p-4"
          style={{ borderTop: "1px solid var(--border)", backgroundColor: "var(--surface)" }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Describe what you're feeling…"
            aria-label="Message Omni"
            disabled={sending || !activeId}
            className="flex-1 rounded-full px-5 py-3 text-[0.95rem] outline-none"
            style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
          />
          <Button type="submit" disabled={sending || !draft.trim()} aria-label="Send">
            <Send size={16} />
          </Button>
        </form>
      </Card>
    </div>
  );
}

function Opener() {
  return (
    <div className="mx-auto max-w-md py-10 text-center">
      <h2 className="text-2xl">Ask Omni</h2>
      <p className="mt-2.5" style={{ color: "var(--ink-muted)" }}>
        Six specialists read your records and deliberate. They're allowed to disagree, and to say
        they don't know.
      </p>
      <p className="mt-4 text-sm" style={{ color: "var(--ink-faint)" }}>
        Try: “I've been exhausted for two weeks and my heart races when I stand.”
      </p>
    </div>
  );
}

function UserBubble({ message }) {
  return (
    <div className="flex justify-end">
      <div
        className="max-w-[75%] rounded-3xl rounded-br-lg px-5 py-3"
        style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
      >
        {message.body}
      </div>
    </div>
  );
}

function Thinking() {
  return (
    <div className="flex flex-col gap-2">
      <Eyebrow>Omni is deliberating</Eyebrow>
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20 w-32" />
        ))}
      </div>
    </div>
  );
}

function OmniReply({ message }) {
  const { blocks = {} } = message;
  const { deliberation = [], verdict, followUp, whyAsking, redFlags, withheldScopes } = blocks;

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-5 sm:p-6">
        <Eyebrow>Omni</Eyebrow>
        <p className="mt-2 text-[1.05rem]">{message.body}</p>

        {redFlags?.length > 0 && (
          <div
            className="mt-4 flex gap-3 rounded-2xl p-4"
            style={{ backgroundColor: "var(--rose-bg)", color: "var(--rose)" }}
          >
            <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">Red flags detected: {redFlags.join(", ")}</p>
              <p className="mt-1 text-sm">
                The usual questions are skipped here. This needs in-person assessment now.
              </p>
            </div>
          </div>
        )}

        {followUp && (
          <div className="mt-5 rounded-2xl p-4" style={{ backgroundColor: "var(--surface-2)" }}>
            <p className="font-semibold">{followUp}</p>
            {whyAsking && (
              <p className="mt-1.5 text-sm" style={{ color: "var(--ink-muted)" }}>
                <span className="font-semibold">Why I'm asking:</span> {whyAsking}
              </p>
            )}
          </div>
        )}

        {withheldScopes?.length > 0 && (
          <p className="mt-4 text-sm" style={{ color: "var(--ink-faint)" }}>
            Reasoning without {withheldScopes.length} withheld consent scope
            {withheldScopes.length > 1 ? "s" : ""}. Specialists that depend on those data abstained.
          </p>
        )}
      </Card>

      {deliberation.length > 0 && (
        <div>
          <Eyebrow className="mb-2.5">Panel deliberation · {deliberation.length} specialists</Eyebrow>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {deliberation.map((position) => (
              <SpecialistCard key={position.key} position={position} />
            ))}
          </div>
        </div>
      )}

      {verdict && <Verdict verdict={verdict} />}
    </div>
  );
}

function SpecialistCard({ position }) {
  const Icon = ICONS[position.icon] || Activity;
  const stance = STANCE[position.stance] || STANCE.abstain;
  const muted = position.stance === "abstain";

  return (
    <Card className="p-4" style={{ opacity: muted ? 0.78 : 1 }}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon size={15} style={{ color: "var(--ink-faint)" }} aria-hidden="true" />
          <span className="text-sm font-bold">{position.specialty}</span>
        </div>
        <Badge tone={stance.tone}>{stance.label}</Badge>
      </div>
      <p className="mt-2.5 text-sm" style={{ color: "var(--ink-muted)" }}>
        {position.statement}
      </p>
      {position.confidence !== "none" && (
        <p className="label-eyebrow mt-3">Confidence · {position.confidence}</p>
      )}
    </Card>
  );
}

function Verdict({ verdict }) {
  if (verdict.abstained) {
    return (
      <Card className="p-6" style={{ borderColor: "var(--border-strong)" }}>
        <Eyebrow>Verdict</Eyebrow>
        <h3 className="mt-2 text-xl">{verdict.summary}</h3>
        <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
          {verdict.detail}
        </p>
      </Card>
    );
  }

  return (
    <Card
      className="p-6"
      style={verdict.urgent ? { borderColor: "var(--rose)", backgroundColor: "var(--rose-bg)" } : undefined}
    >
      <Eyebrow>{verdict.urgent ? "Urgent" : "Verdict"}</Eyebrow>
      <h3 className="mt-2 text-xl">{verdict.summary}</h3>
      {verdict.dissentNote && (
        <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
          {verdict.dissentNote}
        </p>
      )}

      <div className="mt-5 flex flex-col gap-4">
        {verdict.stages.map((stage) => (
          <div key={stage.stage}>
            <Eyebrow>{stage.stage}</Eyebrow>
            <ul className="mt-1.5 flex flex-col gap-1.5">
              {stage.actions.map((action) => (
                <li key={action} className="flex gap-2.5 text-sm">
                  <span
                    className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: "var(--accent)" }}
                  />
                  {action}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {!verdict.urgent && verdict.stages.length > 0 && (
        <Button
          variant="accent"
          className="mt-6"
          onClick={() => toast.success("Plan confirmed", { description: "Saved to your care timeline." })}
        >
          Confirm this plan
        </Button>
      )}
    </Card>
  );
}
