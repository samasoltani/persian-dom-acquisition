# -*- coding: utf-8 -*-
"""
قدم ۰۳: تبدیل لایه‌ی %xmor به جدول و بررسی نشانه‌ی «را/رو»

هدف:
  ۱) هر گفته و هر واژه‌ی %xmor را به جدول تبدیل کنیم (با برچسب‌های یکدست‌شده)
  ۲) همه‌ی نشانه‌های «را» (ptl|ro و ptl|ra) را همراه با واژه‌ی میزبانشان بشماریم
  ۳) موارد مشکوک را گزارش کنیم تا بدانیم چقدر می‌توان به %xmor تکیه کرد

ورودی:
  data/raw/Lilia/*.cha
  data/raw/Minu/*.cha

خروجی:
  data/processed/03-utterances.csv     یک ردیف برای هر گفته
  data/processed/03-tokens.csv         یک ردیف برای هر واژه‌ی %xmor
  results/tables/03-marker_report.txt  گزارش نشانه‌ی «را»
"""
import re
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROC_DIR = PROJECT_DIR / "data" / "processed"
OUT_DIR = PROJECT_DIR / "results" / "tables"
PROC_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHILDREN = ["Lilia", "Minu"]
MARKER_LEMMAS = {"ro", "ra"}


# ------------------------------------------------------------
# خواندن فایل CHAT
# ------------------------------------------------------------
def read_chat_lines(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = []
    for raw in text.splitlines():
        if raw.startswith("\t") and lines:
            lines[-1] += " " + raw.strip()
        else:
            lines.append(raw.rstrip())
    return lines


def parse_age(age_str):
    m = re.match(r"^(\d+);(\d+)?\.?(\d+)?", age_str.strip())
    if not m:
        return None
    return round(int(m.group(1)) * 12 + int(m.group(2) or 0) + int(m.group(3) or 0) / 30, 1)


def strip_timing(text):
    return re.sub(r"\x15.*?\x15", "", text).strip()


# ------------------------------------------------------------
# تجزیه‌ی یک واژه‌ی %xmor
# نمونه: neg#prog#v:lv|dadæn&pres-3s
#   prefixes = NEG PROG   pos = v:lv   lemma = dadæn
#   features = PRES       suffixes = 3S
# ------------------------------------------------------------
def parse_xmor_word(word):
    if "|" not in word:
        return None  # علائم پایان گفته مثل . ? +...
    left, rest = word.split("|", 1)
    left = left.replace("_", "#")            # neg_prog# -> neg#prog#
    parts = left.split("#")
    pos = parts[-1].lower()
    prefixes = [p.upper() for p in parts[:-1] if p]
    lemma = re.split(r"[&-]", rest, maxsplit=1)[0]
    features = [f.upper() for f in re.findall(r"&([^&\-]+)", rest)]
    suffixes = [s.upper() for s in re.findall(r"-([^&\-]+)", rest)]
    return {
        "pos": pos,
        "lemma": lemma,
        "prefixes": " ".join(prefixes),
        "features": " ".join(features),
        "suffixes": " ".join(suffixes),
        "raw": word,
    }


# ------------------------------------------------------------
# خواندن همه‌ی فایل‌ها
# ------------------------------------------------------------
utt_rows = []
tok_rows = []

for child in CHILDREN:
    for path in sorted((RAW_DIR / child).glob("*.cha")):
        lines = read_chat_lines(path)

        age_months, roles = None, {}
        for line in lines:
            if line.startswith("@ID:"):
                f = line[4:].strip().split("|")
                if len(f) >= 8:
                    roles[f[2]] = f[7]
                    if f[2] == "CHI" and f[3]:
                        age_months = parse_age(f[3])

        current = None
        utt_index = 0
        for line in lines:
            if line.startswith("*"):
                m = re.match(r"^\*(\w+):\s*(.*)$", line)
                if not m:
                    continue
                utt_index += 1
                current = {
                    "utt_id": f"{child}_{path.stem}_{utt_index:05d}",
                    "child": child,
                    "file": path.name,
                    "age_months": age_months,
                    "speaker": m.group(1),
                    "role": roles.get(m.group(1), "?"),
                    "text": strip_timing(m.group(2)),
                    "xmor": "",
                }
                utt_rows.append(current)
            elif line.startswith("%xmor:") and current is not None:
                current["xmor"] = line[len("%xmor:"):].strip()

# تبدیل %xmor هر گفته به واژه‌ها
for u in utt_rows:
    position = 0
    for chunk in u["xmor"].split():
        for word in chunk.split("~"):            # adj|xub~v|budæn -> دو واژه
            parsed = parse_xmor_word(word)
            if parsed is None:
                continue
            parsed.update({
                "utt_id": u["utt_id"], "child": u["child"], "file": u["file"],
                "age_months": u["age_months"], "speaker": u["speaker"],
                "role": u["role"], "position": position,
            })
            parsed["is_marker"] = int(parsed["pos"] == "ptl" and parsed["lemma"].lower() in MARKER_LEMMAS)
            tok_rows.append(parsed)
            position += 1

utts = pd.DataFrame(utt_rows)
toks = pd.DataFrame(tok_rows)

# واژه‌ی میزبان = واژه‌ی قبلی در همان گفته
toks["prev_pos"] = toks.groupby("utt_id")["pos"].shift(1)
toks["prev_lemma"] = toks.groupby("utt_id")["lemma"].shift(1)
toks["prev_suffixes"] = toks.groupby("utt_id")["suffixes"].shift(1)

utts.to_csv(PROC_DIR / "03-utterances.csv", index=False, encoding="utf-8-sig")
toks.to_csv(PROC_DIR / "03-tokens.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# گزارش
# ------------------------------------------------------------
out = []
has_xmor = utts["xmor"] != ""
out.append(f"گفته‌ها: {len(utts)} | دارای %xmor: {has_xmor.sum()} ({has_xmor.mean():.1%})")
out.append(f"واژه‌های %xmor: {len(toks)}")
out.append("")

markers = toks[toks["is_marker"] == 1].copy()
markers["group"] = markers["speaker"].where(markers["speaker"] == "CHI", "ADULT/OTHER")

out.append("=" * 70)
out.append("۱) تعداد نشانه‌ی «را» به تفکیک کودک و گوینده")
out.append("=" * 70)
out.append(markers.groupby(["child", "speaker", "role"]).size()
           .rename("markers").reset_index()
           .sort_values(["child", "markers"], ascending=[True, False]).to_string(index=False))
out.append("")

out.append("=" * 70)
out.append("۲) صورت نوشتاریِ نشانه در %xmor")
out.append("=" * 70)
out.append(markers["raw"].value_counts().to_string())
out.append("")

out.append("=" * 70)
out.append("۳) نوع واژه‌ی میزبان (واژه‌ی قبل از «را»)")
out.append("=" * 70)
host = markers.groupby(["child", "group"])["prev_pos"].value_counts(dropna=False).rename("n").reset_index()
for (child, group), g in host.groupby(["child", "group"]):
    out.append(f"\n{child} | {group}:")
    out.append(g[["prev_pos", "n"]].head(15).to_string(index=False))
out.append("")

# موارد مشکوک: «را» بدون میزبان اسمی/ضمیری
NOMINAL = ("n", "pro", "wh", "qn", "adj", "num")
suspicious = markers[~markers["prev_pos"].fillna("").str.startswith(NOMINAL)]
out.append("=" * 70)
out.append(f"۴) «را» با میزبانِ غیرِاسمی یا بدون میزبان: {len(suspicious)} مورد از {len(markers)}")
out.append("=" * 70)
out.append(suspicious["prev_pos"].value_counts(dropna=False).head(15).to_string())
out.append("\nنمونه‌ها:")
text_by_utt = utts.set_index("utt_id")
for _, r in suspicious.head(20).iterrows():
    u = text_by_utt.loc[r["utt_id"]]
    out.append(f"  [{r['utt_id']}] *{r['speaker']}: {u['text']}")
    out.append(f"      %xmor: {u['xmor']}")
out.append("")

# ناهماهنگی: خط اصلی «ro/ra/o» جدا دارد ولی %xmor نشانه ندارد
utts_with_marker = set(markers["utt_id"])
surface_has = utts["text"].str.contains(r"(?:^|\s)(?:ro|ra|o)(?:\s|$)", regex=True)
mismatch = utts[has_xmor & surface_has & ~utts["utt_id"].isin(utts_with_marker)]
out.append("=" * 70)
out.append(f"۵) خط اصلی ro/ra/o جدا دارد ولی %xmor نشانه ندارد: {len(mismatch)} گفته")
out.append("=" * 70)
for _, u in mismatch.head(20).iterrows():
    out.append(f"  [{u['utt_id']}] *{u['speaker']}: {u['text']}")
    out.append(f"      %xmor: {u['xmor']}")

report = "\n".join(out)
(OUT_DIR / "03-marker_report.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\n✅ جدول‌ها در {PROC_DIR} و گزارش در {OUT_DIR / '03-marker_report.txt'} ذخیره شد.")
