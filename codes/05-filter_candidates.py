# -*- coding: utf-8 -*-
"""
قدم ۰۵: پالایشِ نامزدهای مفعولِ بی‌نشان

مشکلِ قدم ۰۴: بیشترِ نامزدها مفعول نبودند، بلکه
  - نهادِ جمله‌های اسنادی بودند («این شیره»، «کجاست»)          -> فعلِ ربطی/ناگذر
  - فاعلِ ضمیری بودند («من میام»، «شما بگو»)                   -> مطابقه‌ی شخص
  - منادا بودند («مامان، بده»، «بابا، بذارش اینجا»)            -> ویرگول پس از واژه‌ی اول
  - با فعلی آمده بودند که فقط یکی‌دو بار (احتمالاً به خطا) «را» گرفته

این قدم پنج صافی را به‌ترتیب اعمال می‌کند و می‌گوید هر صافی چند نامزد را حذف کرده.
هدفِ این قدم حذفِ موارد قطعاً نادرست است؛ تأییدِ نهایی دستی است (قدم بعد).

ورودی:
  data/processed/03-tokens.csv
  data/processed/04-marked_objects.csv
  data/processed/04-unmarked_candidates.csv

خروجی:
  data/processed/05-unmarked_candidates_filtered.csv
  results/tables/05-filter_report.txt
"""
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = PROJECT_DIR / "data" / "processed"
OUT_DIR = PROJECT_DIR / "results" / "tables"

# صافیِ ۱: کمینه‌ی تعدادِ «را» برای اینکه فعلی «رایی» حساب شود
MIN_RA = 3

# صافیِ ۲: فعل‌هایی (یا فعل‌های سبکی) که مفعولِ مستقیم نمی‌گیرند
NON_OBJECT_VERBS = {
    "budæn", "shodæn", "amædæn", "ræftæn", "mandæn", "neshæstæn",
    "oftadæn", "xabidæn", "istadæn", "dævidæn", "gæshtæn", "residæn",
}

# صافیِ ۳: شخص و شمارِ ضمایرِ شخصی (برای مطابقه با فعل)
PRONOUN_PERSON = {
    "mæn": "1S", "to": "2S", "ma": "1P", "shoma": "2P",
    "ishun": "3P", "ina": "3P", "una": "3P", "u": "3S", "ishan": "3P",
}
PERSONS = {"1S", "2S", "3S", "1P", "2P", "3P"}

toks = pd.read_csv(PROC_DIR / "03-tokens.csv", keep_default_na=False)
marked = pd.read_csv(PROC_DIR / "04-marked_objects.csv", keep_default_na=False)
cands = pd.read_csv(PROC_DIR / "04-unmarked_candidates.csv", keep_default_na=False)

# دسترسیِ سریع به هر واژه با (utt_id, position)
tok_index = toks.set_index(["utt_id", "position"])


def verb_lemma(key):
    return key.split("_")[-1]


def verb_person(row):
    """شخص/شمارِ فعل از برچسب‌های %xmor (مثلاً PRES 1S)."""
    try:
        t = tok_index.loc[(row["utt_id"], int(row["verb_position"]))]
    except (KeyError, ValueError):
        return ""
    tags = set(f"{t['features']} {t['suffixes']}".split())
    found = tags & PERSONS
    if found:
        return sorted(found)[0]
    if "IMP" in tags or "IMP" in t["prefixes"].split():
        return "2S"
    return ""


def is_vocative(row):
    """واژه‌ی اولِ گفته که پس از آن ویرگول آمده (مامان ، بده)."""
    words = str(row["text"]).split()
    return int(row["host_position"]) == 0 and len(words) > 1 and words[1] == ","


cands["verb_lemma"] = cands["verb_key"].map(verb_lemma)
cands["verb_person"] = cands.apply(verb_person, axis=1)

# شمارشِ «را» برای هر فعل (بدون گوینده‌های EXCLUDE)
ra_count = marked[marked["group"] != "EXCLUDE"].groupby("verb_key").size()
cands["verb_ra_count"] = cands["verb_key"].map(ra_count).fillna(0).astype(int)

log = []
n0 = len(cands)
log.append(f"نامزدهای اولیه (قدم ۰۴): {n0}")

steps = [
    ("۱) فعل کمتر از {} بار «را» گرفته".format(MIN_RA),
     lambda d: d["verb_ra_count"] < MIN_RA),
    ("۲) فعلِ ربطی/ناگذر (بودن، شدن، اومدن، رفتن، ...)",
     lambda d: d["verb_lemma"].isin(NON_OBJECT_VERBS)),
    ("۳) ضمیرِ شخصی با شخصِ یکسان با فعل (فاعل)",
     lambda d: d["host_pos"].str.startswith("pro") & ~d["host_pos"].str.startswith("pro:dem")
               & (d["host_lemma"].map(PRONOUN_PERSON).fillna("") == d["verb_person"])
               & (d["verb_person"] != "")),
    ("۴) منادا (واژه‌ی اول + ویرگول)",
     lambda d: d.apply(is_vocative, axis=1)),
    ("۵) پرسش‌واژه‌ی «کی» (معمولاً فاعل)",
     lambda d: d["host_lemma"].isin({"ki"})),
]

removed_examples = {}
for label, rule in steps:
    mask = rule(cands)
    removed_examples[label] = cands[mask].head(5)
    log.append(f"{label}: حذف {int(mask.sum())} | باقی‌مانده {int((~mask).sum())}")
    cands = cands[~mask].copy()

cands.to_csv(PROC_DIR / "05-unmarked_candidates_filtered.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# گزارش
# ------------------------------------------------------------
out = ["=" * 70, "اثرِ هر صافی", "=" * 70, *log, ""]

out += ["=" * 70, "نمونه‌ای از موارد حذف‌شده در هر صافی (برای کنترل)", "=" * 70]
for label, ex in removed_examples.items():
    out.append(f"\n{label}")
    for _, r in ex.iterrows():
        out.append(f"   {r['host_lemma']} + {r['verb_key']}  |  *{r['speaker']}: {r['text']}")
out.append("")

out += ["=" * 70, "تعدادِ نهایی به تفکیکِ کودک و گروه", "=" * 70]
summary = pd.concat([
    marked.groupby(["child", "group"]).size().rename("marked"),
    cands.groupby(["child", "group"]).size().rename("unmarked_candidates"),
], axis=1).fillna(0).astype(int)
out.append(summary.to_string())
out.append("")

out += ["=" * 70, "نمونه‌های تصادفی از نامزدهای باقی‌مانده", "=" * 70]
for child in ["Lilia", "Minu"]:
    for group in ["CHILD", "INPUT"]:
        sub = cands[(cands["child"] == child) & (cands["group"] == group)]
        out.append(f"\n--- {child} | {group} ({len(sub)} نامزد) ---")
        for i, (_, r) in enumerate(sub.sample(min(15, len(sub)), random_state=2).iterrows(), 1):
            out.append(f"  {i:2d}. {r['host_lemma']} + {r['verb_key']}  |  *{r['speaker']}: {r['text']}")

report = "\n".join(out)
(OUT_DIR / "05-filter_report.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\n✅ گزارش در {OUT_DIR / '05-filter_report.txt'} ذخیره شد.")
