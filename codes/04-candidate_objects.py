# -*- coding: utf-8 -*-
"""
قدم ۰۴: فعل‌های «رایی» و نامزدهای مفعولِ بی‌نشان

ایده (محدوده‌ی تغییرپذیری / envelope of variation):
  فقط جایگاه‌هایی شمرده می‌شوند که «را» در آن‌ها ممکن است.
  «کتاب افتاد» (فاعل) نباید شمرده شود؛ «کتاب خریدم» (مفعولِ بی‌نشان) باید شمرده شود.

روش:
  ۱) فعلِ هر «را» = نخستین فعلِ اصلیِ بعد از آن (فعل مرکب = جزء غیرفعلی + فعل سبک)
  ۲) فهرستِ «فعل‌های رایی» = فعل‌هایی که دست‌کم یک بار در پیکره با «را» آمده‌اند
  ۳) میزبانِ هر «را» = نزدیک‌ترین واژه‌ی اسمی در سمتِ چپ (نه لزوماً واژه‌ی قبلی)
  ۴) نامزدِ مفعولِ بی‌نشان = اسم/ضمیری درست پیش از یک فعلِ رایی، بدون «را»
     و بدون حرف اضافه پیش از آن

ورودی:
  data/processed/03-utterances.csv
  data/processed/03-tokens.csv

خروجی:
  data/processed/04-marked_objects.csv
  data/processed/04-unmarked_candidates.csv
  results/tables/04-ra_verbs.csv
  results/tables/04-candidates_report.txt
"""
import random
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = PROJECT_DIR / "data" / "processed"
OUT_DIR = PROJECT_DIR / "results" / "tables"
random.seed(1)

# ------------------------------------------------------------
# گروه‌بندیِ گوینده‌ها
# ------------------------------------------------------------
INPUT_SPEAKERS = {"MOT", "FAT", "SOM", "CAR", "AUN", "UCL"}


def speaker_group(code):
    if code == "CHI":
        return "CHILD"
    if code in INPUT_SPEAKERS:
        return "INPUT"
    if code == "BRO":
        return "SIBLING"
    return "EXCLUDE"


# فعل‌های کمکی/وجهی که فعلِ اصلیِ «را» نیستند
MODAL_LEMMAS = {"tævanestæn", "xastæn", "bayestæn"}

# واژه‌هایی که %xmor قید برچسب زده ولی می‌توانند مفعول باشند (همه، اینجا، ...)
ADV_OBJECT_LEMMAS = {"hæme", "inja", "unja", "hæmeja", "hæmin", "hæmun"}

NOMINAL_POS_PREFIX = ("n", "pro", "wh", "qn", "num", "pv:n")


def is_main_verb(tok):
    pos = tok["pos"]
    if not pos.startswith("v"):
        return False
    if pos in ("v:aux", "v:mod") or pos.startswith("v:aux") or pos.startswith("v:mod"):
        return False
    if tok["lemma"] in MODAL_LEMMAS:
        return False
    return True


def is_nominal(tok):
    return tok["pos"].startswith(NOMINAL_POS_PREFIX) or tok["lemma"] in ADV_OBJECT_LEMMAS


def verb_key(tokens, i):
    """کلیدِ فعل: برای فعل سبک، جزء غیرفعلی + فعل (مثلاً baz_kærdæn)."""
    tok = tokens[i]
    if tok["pos"].startswith("v:lv") and i > 0 and tokens[i - 1]["pos"].startswith("pv"):
        return f"{tokens[i - 1]['lemma']}_{tok['lemma']}"
    return tok["lemma"]


def verb_start(tokens, i):
    """شروعِ مجموعه‌ی فعلی (اگر جزء غیرفعلی دارد، از آن‌جا)."""
    if tokens[i]["pos"].startswith("v:lv") and i > 0 and tokens[i - 1]["pos"].startswith("pv"):
        return i - 1
    return i


# ------------------------------------------------------------
# خواندن داده
# ------------------------------------------------------------
utts = pd.read_csv(PROC_DIR / "03-utterances.csv", keep_default_na=False)
toks = pd.read_csv(PROC_DIR / "03-tokens.csv", keep_default_na=False)
utt_info = utts.set_index("utt_id")[["text", "xmor"]]

marked_rows = []
clauses = []   # (utt_id, verb index) هایی که «را» دارند؛ برای حذف از نامزدهای بی‌نشان

for utt_id, g in toks.groupby("utt_id", sort=False):
    tokens = g.sort_values("position").to_dict("records")
    for i, tok in enumerate(tokens):
        if tok["is_marker"] != 1:
            continue
        # فعلِ اصلیِ بعد از «را»
        v_idx = next((j for j in range(i + 1, len(tokens)) if is_main_verb(tokens[j])), None)
        # میزبان: نزدیک‌ترین واژه‌ی اسمی در ۴ واژه‌ی قبل
        h_idx = next((j for j in range(i - 1, max(i - 5, -1), -1) if is_nominal(tokens[j])), None)
        host = tokens[h_idx] if h_idx is not None else None
        if v_idx is not None:
            clauses.append((utt_id, v_idx))
        marked_rows.append({
            "utt_id": utt_id, "child": tok["child"], "file": tok["file"],
            "age_months": tok["age_months"], "speaker": tok["speaker"],
            "group": speaker_group(tok["speaker"]),
            "host_lemma": host["lemma"] if host else "",
            "host_pos": host["pos"] if host else "",
            "host_suffixes": host["suffixes"] if host else "",
            "host_distance": (i - h_idx) if h_idx is not None else None,
            "verb_key": verb_key(tokens, v_idx) if v_idx is not None else "",
            "marked": 1,
        })

marked = pd.DataFrame(marked_rows)

# ------------------------------------------------------------
# فهرستِ فعل‌های رایی (از همه‌ی گوینده‌ها به‌جز EXCLUDE)
# ------------------------------------------------------------
ra_verbs = (marked[(marked["verb_key"] != "") & (marked["group"] != "EXCLUDE")]
            .groupby("verb_key").size().rename("ra_count")
            .sort_values(ascending=False).reset_index())
RA_VERBS = set(ra_verbs["verb_key"])
ra_verbs.to_csv(OUT_DIR / "04-ra_verbs.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# نامزدهای مفعولِ بی‌نشان
# ------------------------------------------------------------
marked_clauses = set(clauses)
cand_rows = []

for utt_id, g in toks.groupby("utt_id", sort=False):
    tokens = g.sort_values("position").to_dict("records")
    for v_idx, tok in enumerate(tokens):
        if not is_main_verb(tok):
            continue
        if (utt_id, v_idx) in marked_clauses:
            continue                           # این بند مفعولِ نشان‌دار دارد
        key = verb_key(tokens, v_idx)
        if key not in RA_VERBS:
            continue                           # فعلی که هرگز «را» نگرفته (مثل افتادن)
        k = verb_start(tokens, v_idx) - 1      # واژه‌ی درست قبل از مجموعه‌ی فعلی
        if k < 0 or not is_nominal(tokens[k]) or tokens[k]["pos"].startswith("pv"):
            continue
        if k > 0 and tokens[k - 1]["pos"].startswith("prep"):
            continue                           # گروهِ حرف‌اضافه‌ای، نه مفعول
        noun = tokens[k]
        cand_rows.append({
            "utt_id": utt_id, "child": noun["child"], "file": noun["file"],
            "age_months": noun["age_months"], "speaker": noun["speaker"],
            "group": speaker_group(noun["speaker"]),
            "host_lemma": noun["lemma"], "host_pos": noun["pos"],
            "host_suffixes": noun["suffixes"], "host_distance": None,
            "verb_key": key, "marked": 0,
        })

cands = pd.DataFrame(cand_rows)

for df in (marked, cands):
    df["text"] = df["utt_id"].map(utt_info["text"])
    df["xmor"] = df["utt_id"].map(utt_info["xmor"])

marked.to_csv(PROC_DIR / "04-marked_objects.csv", index=False, encoding="utf-8-sig")
cands.to_csv(PROC_DIR / "04-unmarked_candidates.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# گزارش
# ------------------------------------------------------------
out = []
out.append("=" * 70)
out.append("۱) مفعول‌های نشان‌دار و نامزدهای بی‌نشان به تفکیک کودک و گروهِ گوینده")
out.append("=" * 70)
summary = pd.concat([
    marked.groupby(["child", "group"]).size().rename("marked"),
    cands.groupby(["child", "group"]).size().rename("unmarked_candidates"),
], axis=1).fillna(0).astype(int)
summary["marked_share"] = (summary["marked"] / (summary["marked"] + summary["unmarked_candidates"])).round(3)
out.append(summary.to_string())
out.append("")

out.append("=" * 70)
out.append(f"۲) فعل‌های رایی: {len(ra_verbs)} فعل؛ ۳۰ فعلِ پربسامد")
out.append("=" * 70)
out.append(ra_verbs.head(30).to_string(index=False))
out.append("")

out.append("=" * 70)
out.append("۳) «را»هایی که فعل یا میزبان برایشان پیدا نشد")
out.append("=" * 70)
out.append(f"بدون فعل: {(marked['verb_key'] == '').sum()} | بدون میزبان: {(marked['host_lemma'] == '').sum()} از {len(marked)}")
out.append("")

out.append("=" * 70)
out.append("۴) نوعِ میزبانِ «را» (پس از جست‌وجو به عقب)")
out.append("=" * 70)
out.append(marked.groupby("group")["host_pos"].value_counts().rename("n")
           .groupby(level=0).head(10).to_string())
out.append("")

out.append("=" * 70)
out.append("۵) نمونه‌های تصادفی از نامزدهای بی‌نشان (برای برآوردِ دقت)")
out.append("=" * 70)
for child in ["Lilia", "Minu"]:
    for group in ["CHILD", "INPUT"]:
        sub = cands[(cands["child"] == child) & (cands["group"] == group)]
        out.append(f"\n--- {child} | {group} ({len(sub)} نامزد) ---")
        for _, r in sub.sample(min(15, len(sub)), random_state=1).iterrows():
            out.append(f"  [{r['utt_id']}] {r['host_lemma']} + {r['verb_key']}")
            out.append(f"      *{r['speaker']}: {r['text']}")

report = "\n".join(out)
(OUT_DIR / "04-candidates_report.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\n✅ گزارش در {OUT_DIR / '04-candidates_report.txt'} ذخیره شد.")
