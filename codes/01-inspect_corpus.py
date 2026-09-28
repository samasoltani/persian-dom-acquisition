# -*- coding: utf-8 -*-
"""
قدم ۰۱: بررسی اولیه‌ی پیکره‌ی Family

هدف: قبل از هر تحلیلی بدانیم دقیقاً چه داده‌ای داریم:
  - هر فایل مال کدام کودک است و سن کودک در آن چقدر است
  - چه گوینده‌هایی (کودک، مادر، پدر، ...) در هر فایل حرف زده‌اند
  - هر گوینده چند گفته و چند واژه دارد
  - چه لایه‌های وابسته‌ای (%mor، %gra، ...) در فایل هست

ورودی:
  data/raw/Lilia/*.cha
  data/raw/Minu/*.cha

خروجی:
  results/tables/01-files_overview.csv     (یک ردیف برای هر فایل)
  results/tables/01-speakers_summary.csv   (یک ردیف برای هر کودک × گوینده)
"""
import re
from pathlib import Path
from collections import Counter

import pandas as pd

# ------------------------------------------------------------
# مسیرها: نسبت به پوشه‌ی اصلی پروژه، تا روی هر کامپیوتری کار کند
# ------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUT_DIR = PROJECT_DIR / "results" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHILDREN = ["Lilia", "Minu"]

# کدهای CHAT که واژه‌ی واقعی نیستند
NON_WORDS = {"xxx", "yyy", "www"}


def read_chat_lines(path):
    """فایل CHAT را می‌خواند و سطرهای ادامه‌دار (که با tab شروع می‌شوند)
    را به سطر قبلی می‌چسباند، تا هر گفته یک سطر کامل باشد."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = []
    for raw in text.splitlines():
        if raw.startswith("\t") and lines:
            lines[-1] += " " + raw.strip()
        else:
            lines.append(raw.rstrip())
    return lines


def parse_age(age_str):
    """سن به قالب CHAT مثل 2;03.15 را به ماه تبدیل می‌کند (مثلاً 27.5)."""
    m = re.match(r"^(\d+);(\d+)?\.?(\d+)?", age_str.strip())
    if not m:
        return None
    years = int(m.group(1))
    months = int(m.group(2) or 0)
    days = int(m.group(3) or 0)
    return round(years * 12 + months + days / 30, 1)


def clean_words(utterance_text):
    """کدهای CHAT را حذف می‌کند و فقط واژه‌های واقعی را برمی‌گرداند."""
    t = re.sub(r"\x15.*?\x15", " ", utterance_text)   # کدهای زمان‌بندی صوت
    t = re.sub(r"\[.*?\]", " ", t)                     # توضیحات داخل [ ]
    t = re.sub(r"&=\S+", " ", t)                       # رفتارهای غیرزبانی مثل &=laughs
    t = re.sub(r"[<>+/\"“”.,!?;:()]", " ", t)          # علائم ساختاری و نگارشی
    words = []
    for w in t.split():
        w = w.strip("@&_-")
        if not w or w in NON_WORDS or w.startswith("0") or w.startswith("&"):
            continue
        words.append(w)
    return words


file_rows = []
speaker_rows = []

for child in CHILDREN:
    child_dir = RAW_DIR / child
    files = sorted(child_dir.glob("*.cha"))
    print(f"\n{child}: {len(files)} فایل در {child_dir}")
    if not files:
        print("   ⚠️ هیچ فایلی پیدا نشد. مسیر را بررسی کنید.")
        continue

    for path in files:
        lines = read_chat_lines(path)

        age_months = None
        date = None
        roles = {}                    # کد گوینده -> نقش (مثلاً MOT -> Mother)
        utt_count = Counter()
        word_count = Counter()
        tiers = Counter()

        for line in lines:
            if line.startswith("@ID:"):
                fields = line[4:].strip().split("|")
                if len(fields) >= 8:
                    code, age, role = fields[2], fields[3], fields[7]
                    roles[code] = role
                    if code == "CHI" and age:
                        age_months = parse_age(age)
            elif line.startswith("@Date:"):
                date = line[6:].strip()
            elif line.startswith("*"):
                m = re.match(r"^\*(\w+):\s*(.*)$", line)
                if m:
                    code, text = m.group(1), m.group(2)
                    utt_count[code] += 1
                    word_count[code] += len(clean_words(text))
            elif line.startswith("%"):
                m = re.match(r"^%(\w+):", line)
                if m:
                    tiers[m.group(1)] += 1

        file_rows.append({
            "child": child,
            "file": path.name,
            "date": date,
            "age_months": age_months,
            "speakers": " ".join(sorted(utt_count)),
            "chi_utterances": utt_count.get("CHI", 0),
            "chi_words": word_count.get("CHI", 0),
            "adult_utterances": sum(n for c, n in utt_count.items() if c != "CHI"),
            "adult_words": sum(n for c, n in word_count.items() if c != "CHI"),
            "tiers": " ".join(f"%{t}" for t in sorted(tiers)),
        })

        for code in utt_count:
            speaker_rows.append({
                "child": child,
                "speaker": code,
                "role": roles.get(code, "?"),
                "file": path.name,
                "utterances": utt_count[code],
                "words": word_count[code],
            })

# ------------------------------------------------------------
# ذخیره و گزارش
# ------------------------------------------------------------
files_df = pd.DataFrame(file_rows)
files_df.to_csv(OUT_DIR / "01-files_overview.csv", index=False, encoding="utf-8-sig")

spk_df = pd.DataFrame(speaker_rows)
spk_summary = (
    spk_df.groupby(["child", "speaker", "role"])
    .agg(files=("file", "nunique"), utterances=("utterances", "sum"), words=("words", "sum"))
    .reset_index()
    .sort_values(["child", "utterances"], ascending=[True, False])
)
spk_summary.to_csv(OUT_DIR / "01-speakers_summary.csv", index=False, encoding="utf-8-sig")

print("\n" + "=" * 70)
print("خلاصه‌ی هر کودک")
print("=" * 70)
for child, g in files_df.groupby("child"):
    print(f"\n{child}:")
    print(f"   تعداد فایل: {len(g)}")
    print(f"   بازه‌ی سنی: {g['age_months'].min()} تا {g['age_months'].max()} ماه")
    print(f"   فایل‌های بدون سن کودک: {g['age_months'].isna().sum()}")
    print(f"   گفته‌ها/واژه‌های کودک: {g['chi_utterances'].sum()} / {g['chi_words'].sum()}")
    print(f"   گفته‌ها/واژه‌های بزرگسالان: {g['adult_utterances'].sum()} / {g['adult_words'].sum()}")

print("\n" + "=" * 70)
print("گوینده‌ها (به ترتیب تعداد گفته)")
print("=" * 70)
print(spk_summary.to_string(index=False))

print("\n" + "=" * 70)
print("لایه‌های وابسته‌ی موجود در فایل‌ها")
print("=" * 70)
print(files_df["tiers"].value_counts().to_string())

print(f"\n✅ خروجی‌ها در {OUT_DIR} ذخیره شد.")
