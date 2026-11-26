"""The 40-question eval set. Expected answers come from data/akgec_kb.jsonl; this file writes core/eval_set.jsonl.

`must` is a list of groups; a correct reply matches at least one regex of every group (lower-cased, digit commas removed).
"""

import json
from pathlib import Path

HERE = Path(__file__).parent


def q(qid, category, lang, question, expected, gold, must=(), urgent=()):
    return {"id": qid, "category": category, "lang": lang, "question": question, "expected": expected,
            "gold_ids": gold, "answerable": category not in ("unanswerable", "urgent"),
            "must": [list(group) for group in must], "urgent_events": list(urgent)}


REFUSE = "Not in the knowledge base: must refuse (tier escalate) and state no figure or name."

SET = [
    q("E01", "english", "en", "When was AKGEC established?", "1998", ["GEN-101"], [["1998"]]),
    q("E02", "english", "en", "Which university is the college affiliated to, and what is its college code?",
      "AKTU, Lucknow; college code 027", ["GEN-107"], [["aktu", "abdul kalam", r"a\.k\.t\.u"], [r"\b0?27\b"]]),
    q("E03", "english", "en", "How many B.Tech seats does the college have?", "1,320", ["GEN-103"], [["1320"]]),
    q("E04", "english", "en", "Who is the Director of the college?", "Dr. Hemant Ahuja", ["GEN-106"], [["hemant ahuja"]]),
    q("E05", "english", "en", "What is the minimum attendance needed to sit for the semester exams?", "75%", ["GEN-119"], [[r"\b75"]]),
    q("E06", "english", "en", "What marks do I need in class 12 to be eligible for B.Tech?",
      "45% (40% for SC/ST) with Physics and Maths", ["ADM-102"], [[r"\b45"]]),
    q("E07", "english", "en", "How much is the caution money, and do I get it back?",
      "Rs 5,000, refundable after course completion and no-dues", ["FEE-105"], [["5000", "five thousand"], ["refund", "return", "get it back"]]),
    q("E08", "english", "en", "When will the admit card be available before exams?",
      "About three days before the first theory exam, on the AKTU ERP portal", ["EXM-103"], [["three days", r"\b3 days"]]),
    q("E09", "english", "en", "What insurance cover do the medical charges include?",
      "Hospitalisation up to Rs 50,000 and personal accident up to Rs 1,00,000", ["FEE-106"], [["50000"], ["100000", "1 lakh", "one lakh"]]),
    q("E10", "english", "en", "Which areas do the college buses cover?",
      "Delhi, Noida, Greater Noida, Ghaziabad, Meerut, Anand Vihar, Dilshad Garden", ["TRN-101"], [["delhi"], ["noida"]]),
    q("E11", "english", "en", "How can I get admission to the MCA programme?", "Through CUET-PG scores", ["ADM-104"], [["cuet"]]),

    q("H01", "hinglish", "hinglish", "mera fees receipt kahan milega?", "College ERP portal, Fee Payment section", ["FEE-108"], [["erp"]]),
    q("H02", "hinglish", "hinglish", "library mein kitni books hain?", "1,00,000 se zyada", ["GEN-108"], [["100000", "1 lakh", "ek lakh"]]),
    q("H03", "hinglish", "hinglish", "college ka address kya hai?", "27th Km Stone, Delhi-Meerut Expressway (NH-24), Ghaziabad", ["GEN-104"],
      [["delhi.?meerut", "nh.?24", "27th", "27 ?km"], ["ghaziabad"]]),
    q("H04", "hinglish", "hinglish", "university exam fee kitni hai aur kisko deni hoti hai?",
      "Rs 7,500, seedha university (AKTU) ko", ["FEE-107"], [["7500"], ["university", "aktu"]]),
    q("H05", "hinglish", "hinglish", "re-evaluation ke liye result ke kitne din ke andar apply karna hota hai?",
      "Result ke 7 se 15 din ke andar", ["EXM-105"], [[r"\b7\b", "saat"], [r"\b15\b", "pandrah"]]),
    q("H06", "hinglish", "hinglish", "diploma walon ko direct second year mein admission kaise milta hai?",
      "UPTAC counselling se lateral entry", ["ADM-103"], [["uptac"]]),
    q("H07", "hinglish", "hinglish", "ladkiyon ke hostel mein kitni capacity hai?", "Lagbhag 600", ["HST-103"], [[r"\b600\b"]]),
    q("H08", "hinglish", "hinglish", "agar B.Tech mein mere 72 percent hain to M.Tech tuition fee mein kitni chhoot milegi?",
      "50% tuition waiver", ["ADM-107"], [[r"\b50 ?(%|percent|pratishat|fisdi)", r"\b50\b", "pachaas"]]),
    q("H09", "hinglish", "hinglish", "fees ka demand draft kiske naam pe banana hai?",
      "Ajay Kumar Garg Engineering College, payable at Ghaziabad ya Delhi", ["FEE-101"], [["ajay kumar garg engineering college"]]),
    q("H10", "hinglish", "hinglish", "counselling mein jo paisa diya tha woh college fees mein adjust hoga kya?",
      "Haan, seat acceptance fee first-year fee se ghata di jaati hai", ["FEE-103"],
      [["haan", r"\byes\b", "adjust", "ghata", "deduct", "credit", "kam kar"]]),
    q("H11", "hinglish", "hinglish", "ek semester mein kitne sessional exam hote hain?", "Do sessional aur ek PUT", ["EXM-102"],
      [["two", r"\b2\b", r"\bdo (internal )?(sessional|exam)"]]),

    q("D01", "disfluent", "en", "uh so um I wanted to ask, like, what's the the last date, no wait, sorry, not that, how do I um pay the fees online?",
      "NEFT/RTGS or the Kotak Mahindra Bank online fee portal", ["FEE-101"], [["neft", "rtgs", "kotak", "portal"]]),
    q("D02", "disfluent", "hinglish", "hostel mein... matlab... woh hot water ka kya scene hai, aata hai kya?",
      "Haan, solar water heating sab hostels mein", ["HST-106"], [["solar", "hot water", "garam", "haan", r"\byes\b", "available", "uplabdh"]]),
    q("D03", "disfluent", "en", "I want to know about M.Tech, no actually sorry, MCA, how many seats does MCA have?", "120",
      ["GEN-103"], [[r"\b120\b"]]),
    q("D04", "disfluent", "en", "um who's the the director, sorry, I mean the Director General of the college?", "Dr. R.K. Agarwal",
      ["GEN-106"], [["agarwal", "aggarwal"]]),
    q("D05", "disfluent", "hinglish", "bus pass ke liye na, woh, uh, kaise apply karte hain?",
      "Transport Coordinator desk par route registration form aur fee", ["TRN-102"], [["coordinator"]]),
    q("D06", "disfluent", "en", "can you tell me the hostel timing... no forget timing, how many hostels are there and how many students can stay?",
      "Six hostels, over 1,500 students", ["HST-101"], [["six", r"\b6\b"], ["1500"]]),
    q("D07", "disfluent", "hinglish", "provisional degree kab, I mean kahan se, kahan se milegi?", "College Registrar office",
      ["EXM-107"], [["registrar"]]),
    q("D08", "disfluent", "en", "uh my son, he's in first year, where do the, the first year boys stay?", "Junior Boys Hostel",
      ["HST-102"], [["junior boys"]]),

    q("N01", "unanswerable", "en", "What is the annual tuition fee for B.Tech?", REFUSE, []),
    q("N02", "unanswerable", "hinglish", "hostel ke mess ka timing kya hai?", REFUSE, []),
    q("N03", "unanswerable", "hinglish", "fees late ho gayi to per day kitna fine lagega?", REFUSE, []),
    q("N04", "unanswerable", "en", "What was the highest placement package last year?", REFUSE, []),
    q("N05", "unanswerable", "en", "uh what time do the hostel gates, like, close at night?", REFUSE, []),
    q("N06", "unanswerable", "hinglish", "CSE department ke HOD kaun hain?", REFUSE, []),

    q("U01", "urgent", "en", "my friend just collapsed in the hostel and he's not breathing properly, what do I do right now?",
      "Flag as medical/safety emergency", ["EMG-101", "EMG-102"], urgent=["medical", "safety"]),
    q("U02", "urgent", "hinglish", "aaj fees jama karne ki last date hai aur online payment fail ho raha hai, jaldi batao kya karu",
      "Flag as fee deadline, caller blocked", ["FEE-101"], urgent=["fee_deadline"]),
    q("U03", "urgent", "hinglish", "mera exam bees minute mein hai aur admit card download nahi ho raha",
      "Flag as admit card / exam, caller blocked", ["EXM-103"], urgent=["admit_card", "exam"]),
    q("U04", "urgent", "en", "some seniors are ragging me in the hostel right now, I'm really scared",
      "Flag as harassment/safety", ["GEN-120", "EMG-102"], urgent=["harassment", "safety"]),
]

# The `data-scraped` KB (levels 1-4) reuses ids for different entries and adds facts, so expectations differ there:
# (gold ids, must groups or None to keep, expected answer or None to keep). N04 stays unanswerable.
SCRAPED = {
    "E01": (["GEN-101"], None, None), "E02": (["GEN-107"], None, None), "E03": (["GEN-103"], None, None),
    "E04": (["GEN-106"], None, None), "E05": (["GEN-120"], None, None), "E06": (["ADM-102"], None, None),
    "E07": (["FEE-108", "FEE-101"], [["5000", "five thousand"], ["refund", "return", "distribut", "collect", "get it back"]], None),
    "E08": (["EXM-105"], [[r"3 ?(to|-) ?5", "three to five", "three days", r"\b3 days"]], "3 to 5 days before exams"),
    "E09": (["FEE-109"], None, None),
    "E10": (["TRN-101"], [["noida"], ["anand vihar", "dilshad", "delhi"]], "NCR routes incl. Noida, Anand Vihar, Dilshad Garden"),
    "E11": (["ADM-104"], None, None), "H01": (["FEE-111"], None, None),
    "H02": (["GEN-108"], [["110000", r"1\.1 lakh", "ek lakh das"]], "1,10,000 se zyada"),
    "H03": (["GEN-104"], None, None), "H04": (["FEE-110"], None, None),
    "H05": (["EXM-108"], [[r"\b30\b", "tees"]], "Result ke 30 din ke andar"),
    "H06": (["ADM-103"], None, None), "H07": (["HST-104", "HST-102"], None, None), "H08": (["ADM-107"], None, None),
    "H09": (["FEE-103"], None, None), "H10": (["FEE-105"], None, None), "H11": (["EXM-103"], None, None),
    "D01": (["FEE-103"], None, None), "D02": (["HST-108", "HST-104"], None, None), "D03": (["GEN-103"], None, None),
    "D04": (["GEN-106"], None, None), "D05": (["TRN-103"], [["coordinator", "transport desk"]], "Transport Desk, Admin Block"),
    "D06": (["HST-102"], None, None), "D07": (["EXM-110"], None, None), "D08": (["HST-103", "HST-102"], None, None),
    "N01": (["FEE-101"], [["142156", "111256", "55628"]], "Rs 1,42,156 per year (tuition and development Rs 1,11,256)"),
    "N02": (["HST-106"], [[r"7[:.]30"], [r"12[:.]30"]], "Breakfast 7:30-9, lunch 12:30-2, dinner 7:30-9:30"),
    "N03": (["FEE-106"], [[r"\b100\b", r"\bsau\b"]], "Rs 100 per day"),
    "N05": (["HST-105"], [[r"\b10(:00)? ?(pm|p\.m|baje)", r"\b10\b"]], "10 PM boys, 8 PM girls"),
    "N06": (["GEN-122"], [["anu ch[ao]udhary"]], "Dr. Anu Chaudhary"),
    "U01": (["EMG-101", "EMG-102"], None, None), "U02": (["FEE-103", "FEE-102"], None, None),
    "U03": (["EXM-105"], None, None), "U04": (["EMG-103", "GEN-121"], None, None),
}
for row in SET:
    if row["id"] in SCRAPED:
        gold, must, expected = SCRAPED[row["id"]]
        row["scraped"] = {"gold_ids": gold, **({"must": must} if must else {}), **({"expected": expected} if expected else {}),
                          **({"answerable": True} if must and not row["answerable"] else {})}

if __name__ == "__main__":
    from core.corpus import level

    kb = {i for i, _, _ in level(0)[1]}
    scraped_kb = {i for i, _, _ in level(1)[1]}
    assert all(set(r.get("scraped", {}).get("gold_ids", [])) <= scraped_kb for r in SET)
    count = lambda c: sum(r["category"] == c for r in SET)
    assert len(SET) == 40 and count("unanswerable") == 6 and count("urgent") == 4
    assert len({r["id"] for r in SET}) == 40 and all(set(r["gold_ids"]) <= kb for r in SET)
    assert all(r["must"] for r in SET if r["answerable"])
    (HERE / "eval_set.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in SET), encoding="utf-8")
    print({c: count(c) for c in dict.fromkeys(r["category"] for r in SET)})
