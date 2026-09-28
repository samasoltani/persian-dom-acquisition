# -*- coding: utf-8 -*-
"""
قدم ۰۲: بررسی محتوای لایه‌های وابسته (به‌ویژه %xmor و %xcau)

هدف: پیش از طراحی استخراج مفعول‌ها بدانیم لایه‌های دستیِ پژوهشگر
(%xmor, %xcau) دقیقاً چه چیزی را کدگذاری کرده‌اند، و آیا «را/رو»
یا نقش مفعول در آن‌ها علامت خورده است.

ورودی:
  data/raw/Lilia/*.cha
  data/raw/Minu/*.cha

خروجی:
  results/tables/02-tier_examples.txt     نمونه‌ها برای خواندن
  results/tables/02-xmor_tags.csv         بسامد برچسب‌های %xmor
"""
import re
import random
from pathlib import Path
from collections import Counter

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUT_DIR = PROJECT_DIR / "results" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHILDREN = ["Lilia", "Minu"]
TIERS_TO_SHOW = ["xmor", "xcau", "mor", "gra", "com", "add"]
N_EXAMPLES = 8          # تعداد نمونه برای هر لایه
N_RO_EXAMPLES = 25      # تعداد نمونه‌ی واژه‌های مختوم به -ro/-o
random.seed(1)          # تا خروجی هر بار یکسان باشد


def read_chat_lines(path):
    """سطرهای ادامه‌دار (شروع با tab) را به سطر قبلی می‌چسباند."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = []
    for raw in text.splitlines():
        if raw.startswith("\t") and lines:
            lines[-1] += " " + raw.strip()
        else:
            lines.append(raw.rstrip())
    return lines


def read_utterances(path):
    """هر گفته را همراه با لایه‌های وابسته‌اش برمی‌گرداند:
    {'speaker': 'CHI', 'text': '...', 'tiers': {'xmor': '...', ...}}"""
    utterances = []
    for line in read_chat_lines(path):
        if line.startswith("*"):
            m = re.match(r"^\*(\w+):\s*(.*)$", line)
            if m:
                utterances.append({"speaker": m.group(1), "text": m.group(2), "tiers": {}})
        elif line.startswith("%") and utterances:
            m = re.match(r"^%(\w+):\s*(.*)$", line)
            if m:
                utterances[-1]["tiers"][m.group(1)] = m.group(2)
    return utterances


def strip_timing(text):
    return re.sub(r"\x15.*?\x15", "", text).strip()


# ------------------------------------------------------------
# خواندن همه‌ی گفته‌ها
# ------------------------------------------------------------
all_utts = []
for child in CHILDREN:
    for path in sorted((RAW_DIR / child).glob("*.cha")):
        for u in read_utterances(path):
            u["child"] = child
            u["file"] = path.name
            all_utts.append(u)

print(f"مجموع گفته‌ها: {len(all_utts)}")

out = []  # متن گزارش

# ------------------------------------------------------------
# ۱) نمونه‌های هر لایه
# ------------------------------------------------------------
for tier in TIERS_TO_SHOW:
    with_tier = [u for u in all_utts if tier in u["tiers"]]
    out.append("=" * 80)
    out.append(f"لایه‌ی %{tier}: در {len(with_tier)} گفته")
    out.append("=" * 80)
    for u in random.sample(with_tier, min(N_EXAMPLES, len(with_tier))):
        out.append(f"[{u['child']} | {u['file']}]")
        out.append(f"  *{u['speaker']}: {strip_timing(u['text'])}")
        out.append(f"  %{tier}: {u['tiers'][tier]}")
        # اگر %xmor هم دارد، برای مقایسه نشان بده
        if tier != "xmor" and "xmor" in u["tiers"]:
            out.append(f"  %xmor: {u['tiers']['xmor']}")
        out.append("")

# ------------------------------------------------------------
# ۲) پربسامدترین برچسب‌های %xmor
# هر واژه در %xmor را به قطعه‌هایش (جداشده با | - # & = ~ :) می‌شکنیم
# ------------------------------------------------------------
tag_counter = Counter()
for u in all_utts:
    xmor = u["tiers"].get("xmor")
    if not xmor:
        continue
    for token in xmor.split():
        for piece in re.split(r"[|\-#&=~:]", token):
            if piece:
                tag_counter[piece] += 1

tags_df = pd.DataFrame(tag_counter.most_common(), columns=["piece", "count"])
tags_df.to_csv(OUT_DIR / "02-xmor_tags.csv", index=False, encoding="utf-8-sig")

out.append("=" * 80)
out.append("۶۰ قطعه‌ی پربسامدِ %xmor")
out.append("=" * 80)
out.append(tags_df.head(60).to_string(index=False))
out.append("")

# ------------------------------------------------------------
# ۳) گفته‌هایی که واژه‌ای مختوم به -ro یا -o دارند، همراه با %xmor
# (برای دیدن اینکه «را» در %xmor چطور کدگذاری شده)
# ------------------------------------------------------------
ro_utts = [
    u for u in all_utts
    if "xmor" in u["tiers"] and re.search(r"\w+ro\b|\w+o\b", strip_timing(u["text"]))
]
out.append("=" * 80)
out.append(f"گفته‌های دارای واژه‌ی مختوم به -ro/-o (همراه با %xmor): {len(ro_utts)} گفته؛ {N_RO_EXAMPLES} نمونه")
out.append("=" * 80)
for u in random.sample(ro_utts, min(N_RO_EXAMPLES, len(ro_utts))):
    out.append(f"[{u['child']} | {u['file']}]")
    out.append(f"  *{u['speaker']}: {strip_timing(u['text'])}")
    out.append(f"  %xmor: {u['tiers']['xmor']}")
    out.append("")

report = "\n".join(out)
(OUT_DIR / "02-tier_examples.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\n✅ گزارش در {OUT_DIR / '02-tier_examples.txt'} ذخیره شد.")
