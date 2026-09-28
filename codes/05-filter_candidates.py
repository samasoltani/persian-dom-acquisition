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

# صافیِ ۶: اسم‌هایی که با «کردن» فعل مرکب می‌سازند ولی %xmor اسم برچسب زده
LV_NOUNS = {"kar", "bazi", "komæk", "gerye", "xænde"}

# صافیِ ۷: حرف‌اضافه‌هایی که %xmor گاهی prep برچسب نزده
EXTRA_PREPS = {"vase", "bæra", "bære", "baraye", "bæraye"}

# صافیِ ۸: قیدهای زمان و مکان، و اصطلاح «راست گفتن»
ADVERBIAL_NOUNS = {
    "væqt", "inja", "unja", "hæminja", "hæmunja", "koja", "hær_ja",
    "emruz", "diruz", "færda", "shæb", "sob", "zohr", "æsr", "ælan", "hala",
    "dæfe", "bar", "shænbe", "yekshænbe", "doshænbe", "seshænbe",
    "chaharshænbe", "pænjshænbe", "jome", "rast",
}

toks = pd.read_csv(PROC_DIR / "03-tokens.csv", keep_default_na=False)
marked = pd.read_csv(PROC_DIR / "04-marked_objects.csv", keep_default_na=False)
cands = pd.read_csv(PROC_DIR / "04-unmarked_candidates.csv", keep_default_na=False)

# دسترسیِ سریع به هر واژه با (utt_id, position)
tok_index = toks.set_index(["utt_id", "position"])


def verb_lemma(key):
    return key.split("_")[-1]


def get_tok(utt_id, position):
    try:
        return tok_index.loc[(utt_id, int(position))]
    except (KeyError, ValueError):
        return None


def verb_person(row):
    """شخص/شمارِ فعل از برچسب‌های %xmor (مثلاً PRES 1S).
    در فعل‌های چندجزئی (دیده بودی) شخص روی فعلِ کمکیِ بعدی است."""
    t = get_tok(row["utt_id"], row["verb_position"])
    if t is None:
        return ""
    tags = set(f"{t['features']} {t['suffixes']}".split())
    aux = get_tok(row["utt_id"], int(row["verb_position"]) + 1)
    if aux is not None and str(aux["pos"]).startswith("v:aux"):
        tags |= set(f"{aux['features']} {aux['suffixes']}".split())
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


def bare_lv_noun(row):
    """«کار کردن» به معنای «کار کردن» (فعل مرکب) حذف شود،
    ولی «چی کار کنی»، «یه کاری کرد»، «این کار» بماند؛
    چون این‌جا «کار» یعنی «چه کاری/یک کاری» و مفعول است (چه کاری را انجام دهی).
    قاعده: اگر درست پیش از اسم پرسش‌واژه، کمیت‌نما، اشاره یا صفت آمده باشد، مفعول است."""
    if row["host_lemma"] not in LV_NOUNS or row["verb_lemma"] != "kærdæn":
        return False
    prev = get_tok(row["utt_id"], int(row["host_position"]) - 1)
    if prev is not None and str(prev["pos"]).startswith(("wh", "qn", "pro:dem", "adj", "num")):
        return False
    if "INDEF" in str(row["host_suffixes"]).split():
        return False
    return True


IDIOMS = {("cheshm", "gozashtæn"), ("chesh", "gozashtæn")}   # چشم گذاشتن (قایم‌موشک)


def infinitive_or_passive(row):
    """«لباس عوض کردنت» (مصدر) و «دستش کنده شد» (مجهول) مفعولِ رادار ندارند."""
    v = get_tok(row["utt_id"], row["verb_position"])
    if v is None:
        return False
    if "inf" in str(v["pos"]).split(":"):
        return True
    nxt = get_tok(row["utt_id"], int(row["verb_position"]) + 1)
    return (nxt is not None and str(nxt["lemma"]) == "shodæn"
            and "ptcp" in str(v["pos"]).split(":") + ["ptcp" if "PTCP" in str(v["features"]) else ""])


def inside_pp(row):
    """آیا اسم درونِ گروهِ حرف‌اضافه‌ای است؟
    از اسم به عقب می‌رویم تا وقتی واژه‌ی قبلی وابسته‌ی همین گروهِ اسمی است
    (اشاره، کمیت‌نما، عدد، یا اسمی با کسره‌ی اضافه)، و می‌بینیم به حرف اضافه می‌رسیم یا نه.
    مثال: از + این + کارتا  |  به + این + اسکیته  |  واسه + چی"""
    j = int(row["host_position"]) - 1
    while j >= 0:
        t = get_tok(row["utt_id"], j)
        if t is None:
            return False
        pos, lemma, suffixes = str(t["pos"]), str(t["lemma"]), str(t["suffixes"]).split()
        if pos.startswith("prep") or lemma in EXTRA_PREPS:
            return True
        if pos.startswith(("pro:dem", "qn", "num")) or "EZ" in suffixes:
            j -= 1
            continue
        return False
    return False


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
    ("۶) جزءِ اسمیِ فعلِ مرکب بدون وابسته (کار می‌کنه، بازی کن)",
     lambda d: d.apply(bare_lv_noun, axis=1)),
    ("۷) درونِ گروهِ حرف‌اضافه‌ای (از این کارتا، واسه چی)",
     lambda d: d.apply(inside_pp, axis=1)),
    ("۸) قیدِ زمان/مکان و «راست گفتن»",
     lambda d: d["host_lemma"].isin(ADVERBIAL_NOUNS)),
    ("۹) مصدر یا فعلِ مجهول (عوض کردنت، کنده شد)",
     lambda d: d.apply(infinitive_or_passive, axis=1)),
    ("۱۰) اصطلاح (چشم گذاشتن) و واژه‌های غیرِاسمی (دیگه، آخه)",
     lambda d: d.apply(lambda r: (r["host_lemma"], r["verb_lemma"]) in IDIOMS, axis=1)
               | d["host_lemma"].isin({"dige", "axe", "æxe"})),
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
