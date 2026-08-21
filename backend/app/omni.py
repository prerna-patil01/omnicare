"""Ask Omni — the multi-agent deliberation layer.

Two execution paths, same output contract:

- If `GROQ_API_KEY` is set, the six specialist positions and the final verdict
  are generated through a configurable OpenAI-compatible endpoint, given the
  user's actual stored vitals, twin nodes, and findings as context.
- Otherwise a deterministic clinical reasoning engine derives the same
  structure from those same rows.

The second path is not a stub or canned text: every position is computed from
the querying user's own database records, so two accounts produce genuinely
different deliberations. It exists because the API key is deployment
configuration, and the feature should not be dark without one.

Consent is enforced before either path sees anything (SRS §6.2): a scope the
user has revoked is filtered out of the context, and the agents are told the
data was withheld rather than being given it silently.
"""

import json
import os

from .extensions import db
from . import derive
from .models import ConsentScope, VitalReading

SPECIALISTS = [
    ("cardiology", "Cardiology", "heart"),
    ("endocrinology", "Endocrinology", "activity"),
    ("neurology", "Neurology", "brain"),
    ("nephrology", "Nephrology", "droplet"),
    ("immunology", "Immunology", "shield"),
    ("lifestyle", "Lifestyle Medicine", "leaf"),
]

# Presentations that must bypass the clarifying-question flow entirely.
# SRS gap #1 called out the absence of this; it is enforced here rather than
# left to the model's judgement.
RED_FLAGS = [
    ("chest pain", "Chest pain"),
    ("chest tightness", "Chest tightness"),
    ("crushing", "Crushing chest sensation"),
    ("can't breathe", "Acute breathlessness"),
    ("cant breathe", "Acute breathlessness"),
    ("short of breath", "Acute breathlessness"),
    ("slurred", "Slurred speech"),
    ("face drooping", "Facial droop"),
    ("one side", "Unilateral weakness"),
    ("numb on", "Unilateral numbness"),
    ("worst headache", "Thunderclap headache"),
    ("unconscious", "Loss of consciousness"),
    ("fainted", "Syncope"),
    ("coughing blood", "Haemoptysis"),
    ("vomiting blood", "Haematemesis"),
    ("suicid", "Suicidal ideation"),
]


def check_red_flags(text):
    lowered = (text or "").lower()
    hits = [label for token, label in RED_FLAGS if token in lowered]
    return sorted(set(hits))


def gather_context(user_id):
    """Assemble the clinical picture from the user's *entered* data, filtered
    through granted consent. Every value here traces back to a reading the user
    logged or a biomarker they recorded — nothing is generated."""
    granted = {
        row.key
        for row in db.session.query(ConsentScope).filter_by(user_id=user_id, granted=True)
    }
    withheld = {
        row.key
        for row in db.session.query(ConsentScope).filter_by(user_id=user_id, granted=False)
    }
    context = {"granted": sorted(granted), "withheld": sorted(withheld)}

    if "lifestyle" in granted:
        summary = derive.vitals_summary(user_id, days=30)
        if summary["readingCount"]:
            context["vitals"] = {**summary["summary"], "days": summary["readingCount"]}

    if "digital_twin" in granted:
        twin = derive.twin_for(user_id)
        if twin["sufficient"]:
            context["twin"] = {
                n["key"]: {"risk": n["riskPct"], "status": n["status"]}
                for n in twin["nodes"] if n["measured"]
            }
            context["predispositions"] = twin["predispositions"]

    if "records" in granted:
        finding = derive.finding_for(user_id)
        if finding:
            context["activeFinding"] = finding

    return context


# ---------------------------------------------------------------------------
# Deterministic reasoning engine
# ---------------------------------------------------------------------------

def _position(key, label, icon, stance, statement, confidence):
    return {
        "key": key,
        "specialty": label,
        "icon": icon,
        "stance": stance,          # concur | dissent | abstain
        "statement": statement,
        "confidence": confidence,
    }


def deliberate_locally(question, context):
    """Derive six specialist positions from the user's own entered readings.

    With nothing logged, every specialist abstains — the panel says it has no
    basis rather than making statements about numbers that do not exist."""
    vitals = context.get("vitals")
    twin = context.get("twin", {})
    positions = []

    def risk_of(key):
        return twin.get(key, {}).get("risk")

    # --- Cardiology ---
    heart_risk = risk_of("heart")
    if vitals and heart_risk is not None:
        hr, hrv = vitals["heartRate"], vitals["hrv"]
        if heart_risk >= 45 or hr > 78:
            positions.append(_position(
                "cardiology", "Cardiology", "heart", "concur",
                f"Mean resting heart rate across your logged readings is {hr} bpm, HRV {hrv} ms. "
                f"Cardiovascular load scores {heart_risk}%. This warrants ambulatory blood pressure monitoring.",
                "high" if heart_risk >= 55 else "moderate",
            ))
        else:
            positions.append(_position(
                "cardiology", "Cardiology", "heart", "dissent",
                f"Resting heart rate ({hr} bpm) and HRV ({hrv} ms) sit within your own baseline. "
                "I would not attribute the presentation to cardiac strain.",
                "moderate",
            ))
    else:
        positions.append(_position(
            "cardiology", "Cardiology", "heart", "abstain",
            "No heart-rate readings logged, or lifestyle consent is off. I have no basis for a position.",
            "none",
        ))

    # --- Endocrinology ---
    metabolic_risk = risk_of("metabolic")
    if metabolic_risk is not None:
        if metabolic_risk >= 40:
            positions.append(_position(
                "endocrinology", "Endocrinology", "activity", "concur",
                f"Metabolic system scores {metabolic_risk}%. Glucose handling is the more likely driver here; "
                "an HbA1c and fasting insulin would settle it.",
                "moderate",
            ))
        else:
            positions.append(_position(
                "endocrinology", "Endocrinology", "activity", "dissent",
                f"Metabolic markers score {metabolic_risk}%, which is unremarkable. "
                "I see no endocrine contribution worth pursuing first.",
                "moderate",
            ))
    else:
        positions.append(_position(
            "endocrinology", "Endocrinology", "activity", "abstain",
            "Not enough logged readings to score the metabolic system, or twin consent is off.",
            "none",
        ))

    # --- Neurology ---
    if vitals:
        sleep, stress = vitals["sleep"], vitals["stress"]
        if sleep < 6.5 or stress > 55:
            positions.append(_position(
                "neurology", "Neurology", "brain", "concur",
                f"Sleep averages {sleep} h against a {stress}/100 stress load. Chronic sleep debt of this depth "
                "produces exactly this symptom cluster and compounds every other system here.",
                "high",
            ))
        else:
            positions.append(_position(
                "neurology", "Neurology", "brain", "dissent",
                f"Sleep ({sleep} h) and stress ({stress}/100) are adequate. "
                "I disagree that this is fatigue-driven — look elsewhere first.",
                "moderate",
            ))
    else:
        positions.append(_position(
            "neurology", "Neurology", "brain", "abstain",
            "No sleep or stress readings logged, or lifestyle consent is off.",
            "none",
        ))

    # --- Nephrology ---
    if vitals:
        hydration = vitals["hydrationMl"]
        if hydration < 1800:
            positions.append(_position(
                "nephrology", "Nephrology", "droplet", "concur",
                f"Hydration averages {hydration} ml/day, well under target. This alone can produce the "
                "presentation and is the cheapest thing on this list to correct.",
                "moderate",
            ))
        else:
            positions.append(_position(
                "nephrology", "Nephrology", "droplet", "abstain",
                f"Hydration at {hydration} ml/day is adequate. Without serum creatinine or eGFR "
                "I have no basis for a renal position.",
                "none",
            ))
    else:
        positions.append(_position(
            "nephrology", "Nephrology", "droplet", "abstain",
            "No hydration readings logged, or lifestyle consent is off.",
            "none",
        ))

    # --- Immunology ---
    immune_risk = risk_of("immune")
    if immune_risk is not None and immune_risk >= 40:
        positions.append(_position(
            "immunology", "Immunology", "shield", "concur",
            f"Immune resilience scores {immune_risk}%. With regional influenza activity elevated, "
            "recovery capacity is worth checking with a CBC.",
            "moderate",
        ))
    else:
        positions.append(_position(
            "immunology", "Immunology", "shield", "abstain",
            "Nothing in the available data points to an immune contribution. I defer to the others.",
            "none",
        ))

    # --- Lifestyle Medicine ---
    if vitals:
        positions.append(_position(
            "lifestyle", "Lifestyle Medicine", "leaf", "concur",
            f"Before any investigation: sleep is {vitals['sleep']} h and hydration {vitals['hydrationMl']} ml. "
            "Correcting those two for three weeks would change the interpretation of every other finding here.",
            "high",
        ))
    else:
        positions.append(_position(
            "lifestyle", "Lifestyle Medicine", "leaf", "abstain",
            "Nothing logged yet, so I cannot advise on modifiable factors.",
            "none",
        ))

    return positions


def build_verdict(positions, context, red_flags):
    """Stage a plan from the positions. Abstains outnumbering concurs is an
    explicit 'I don't know yet', not a fabricated answer."""
    if red_flags:
        return {
            "abstained": False,
            "urgent": True,
            "summary": "This needs to be assessed in person now, not by me.",
            "stages": [
                {"stage": "Immediately", "actions": [
                    "Use the SOS control or call 108 for emergency transport.",
                    "Do not drive yourself.",
                ]},
                {"stage": "On arrival", "actions": [
                    "Tell them which symptoms started and when.",
                    "Mention any cardiac or neurological history.",
                ]},
            ],
            "flags": red_flags,
        }

    concurring = [p for p in positions if p["stance"] == "concur"]
    abstaining = [p for p in positions if p["stance"] == "abstain"]

    if len(abstaining) >= 4 or not concurring:
        return {
            "abstained": True,
            "urgent": False,
            "summary": "I don't know yet — there isn't enough data to reason from.",
            "detail": (
                "Most of the panel abstained. Either the consent scopes needed for this question "
                "are switched off, or there aren't enough readings on record yet. "
                "Granting the relevant scope or uploading a recent report would let me answer properly."
            ),
            "stages": [],
        }

    ranked = sorted(
        concurring,
        key=lambda p: {"high": 0, "moderate": 1, "none": 2}[p["confidence"]],
    )
    lead = ranked[0]

    stages = [
        {"stage": "This week", "actions": [
            f"Act on {lead['specialty']}'s read first — it carries the most support in the panel.",
            "Log sleep and hydration daily so the next deliberation has cleaner inputs.",
        ]},
        {"stage": "Next two weeks", "actions": [
            a for a in (context.get("activeFinding", {}).get("suggestedNext") or [])
        ] or ["Book a general physician review to order baseline bloods."]},
        {"stage": "Then", "actions": [
            "Re-run this question — the twin updates as new readings land.",
        ]},
    ]

    dissent = [p for p in positions if p["stance"] == "dissent"]
    return {
        "abstained": False,
        "urgent": False,
        "summary": f"{len(concurring)} of 6 specialists converge on {lead['specialty'].lower()} as the lead thread.",
        "dissentNote": (
            f"{dissent[0]['specialty']} disagrees — worth reading their position before you commit."
            if dissent else None
        ),
        "stages": stages,
    }


# ---------------------------------------------------------------------------
# Configurable OpenAI-compatible LLM path
# ---------------------------------------------------------------------------

def llm_available():
    return bool(os.environ.get("GROQ_API_KEY"))


def engine_name():
    return os.environ.get("LLM_MODEL", "openai/gpt-oss-20b") if llm_available() else "local-reasoning"


DELIBERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "followUp": {"type": "string"},
        "whyAsking": {"type": "string"},
        "positions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "specialty": {"type": "string"},
                    "icon": {"type": "string"},
                    "stance": {"type": "string", "enum": ["concur", "dissent", "abstain"]},
                    "statement": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "moderate", "none"]},
                },
                "required": ["key", "specialty", "icon", "stance", "statement", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["followUp", "whyAsking", "positions"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are Omni, the clinical reasoning layer of OmniCare.

Six specialists deliberate on each question: cardiology, endocrinology, neurology,
nephrology, immunology, and lifestyle medicine. They are allowed to disagree, and a
specialist with no basis for a position must abstain rather than invent one.

Ground every statement in the numbers you are given. Never state a figure that is not
in the context. If a consent scope was withheld, the specialists who depend on it
abstain and say the data was not available — do not speculate around the gap.

Frame risk as worth attention rather than as emergency. Speak plainly; avoid jargon
unless it is the precise term."""


def deliberate_with_llm(question, context, history):
    """Generate the panel through an OpenAI-compatible chat endpoint.

    The adapter intentionally uses the standard library so changing providers
    only requires environment variables, not a provider SDK or UI change.
    """
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    transcript = "\n".join(f"{m['role']}: {m['body']}" for m in history[-6:])
    prompt = (
        f"Clinical context (from this patient's records):\n{json.dumps(context, indent=2)}\n\n"
        f"Recent conversation:\n{transcript or '(none)'}\n\n"
        f"Patient asks: {question}\n\n"
        "Return only JSON matching this schema:\n"
        f"{json.dumps(DELIBERATION_SCHEMA)}"
    )
    payload = json.dumps({
        "model": os.environ.get("LLM_MODEL", "openai/gpt-oss-20b"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    request = Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError("Configured LLM request failed") from error

    content = result.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Configured LLM returned no message content")
    answer = json.loads(content)
    if not isinstance(answer.get("positions"), list):
        raise RuntimeError("Configured LLM returned an invalid deliberation")
    return answer


def respond(question, context, history):
    """Produce one Omni turn. Returns (body, blocks)."""
    red_flags = check_red_flags(question)

    if red_flags:
        # Red flags short-circuit the whole deliberation flow.
        return (
            "Stop — this needs urgent in-person assessment.",
            {
                "redFlags": red_flags,
                "deliberation": [],
                "verdict": build_verdict([], context, red_flags),
                "engine": "red-flag-triage",
            },
        )

    engine = "local-reasoning"
    follow_up = None
    why_asking = None
    positions = None

    if llm_available():
        try:
            result = deliberate_with_llm(question, context, history)
            positions = result["positions"]
            follow_up = result.get("followUp")
            why_asking = result.get("whyAsking")
            engine = engine_name()
        except Exception:
            positions = None  # fall through to local engine

    if positions is None:
        positions = deliberate_locally(question, context)
        follow_up = "How many days has this been going on, and is it worse at any particular time?"
        why_asking = (
            "Duration and timing separate the systems above faster than any single test would."
        )

    verdict = build_verdict(positions, context, red_flags)

    return (
        "Here's how the panel read your question.",
        {
            "followUp": follow_up,
            "whyAsking": why_asking,
            "deliberation": positions,
            "verdict": verdict,
            "withheldScopes": context.get("withheld", []),
            "engine": engine,
        },
    )
