"""Rule grading of the <meta>{...}</meta> + spoken-text protocol both arms are asked to follow."""

import json
import re


def parse(text):
    """(meta dict or None, spoken text)."""
    start = text.find("<meta>")
    brace = text.find("{", start) if start >= 0 else -1
    if brace < 0:
        return None, text.strip()
    try:
        meta, end = json.JSONDecoder().raw_decode(text[brace:])
    except json.JSONDecodeError:
        return None, text.strip()
    spoken = text[brace + end:].replace("</meta>", "").replace("```", "").strip()
    return (meta if isinstance(meta, dict) else None), spoken


def normalise(text):
    return re.sub(r"(?<=\d),(?=\d)", "", text.lower())


def view(question, level):
    """The question with the expectations that hold for this knowledge-base level."""
    return question if level == 0 else {**question, **question.get("scraped", {})}


def grade(question, reply):
    meta, spoken = parse(reply)
    tier = str((meta or {}).get("tier", "")).lower()
    row = {"format_ok": meta is not None, "tier": tier, "spoken": spoken, "correct": False,
           "correct_refusal": None, "false_refusal": None, "urgent_ok": None}
    if question["category"] != "urgent" and not question["answerable"]:
        said = normalise(spoken)
        refused = tier == "escalate" or (tier == "partial" and not re.search(r"\d", said))
        row["correct_refusal"] = row["correct"] = bool(meta) and refused
    elif question["category"] == "urgent":
        facts = (meta or {}).get("urgency_facts") or {}
        row["urgent_ok"] = row["correct"] = (facts.get("event_type") in question["urgent_events"]
                                             and bool(facts.get("safety_flag") or facts.get("blocked")))
    else:
        said = normalise(spoken)
        facts_present = all(any(re.search(p, said) for p in group) for group in question["must"])
        row["correct"] = tier in ("confident", "partial") and facts_present
        row["false_refusal"] = bool(meta) and tier in ("escalate", "clarify")
    return row


if __name__ == "__main__":  # self-check
    meta = lambda tier, **f: "<meta>" + json.dumps({"tier": tier, "urgency_facts": f}) + "</meta>\n"
    ask = {"category": "english", "answerable": True, "must": [["5000"], ["refund"]]}
    assert grade(ask, meta("confident") + "It is Rs 5,000 and refundable.")["correct"]
    assert not grade(ask, meta("confident") + "It is Rs 500, refundable.")["correct"]
    assert grade(ask, meta("escalate") + "I do not know.")["false_refusal"]
    assert not grade(ask, "It is 5000, refundable.")["correct"]
    no = {"category": "unanswerable", "answerable": False}
    assert grade(no, meta("escalate") + "I do not have that.")["correct_refusal"]
    assert not grade(no, meta("confident") + "Mess opens at 8.")["correct_refusal"]
    assert not grade(no, meta("partial") + "The fine is 100 rupees.")["correct_refusal"]
    urgent = {"category": "urgent", "urgent_events": ["medical"]}
    assert grade(urgent, meta("escalate", event_type="medical", safety_flag=True) + "x")["urgent_ok"]
    assert not grade(urgent, meta("escalate", event_type="none") + "x")["urgent_ok"]
    later = {**no, "scraped": {"answerable": True, "must": [["100"]]}}
    assert grade(view(later, 1), meta("confident") + "Rs 100 per day.")["correct"] and view(later, 0) is later
    print("grade.py self-check ok")
