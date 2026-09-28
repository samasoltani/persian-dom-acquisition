# Definiteness, Animacy, and the Input: The Emergence of Differential Object Marking in Persian Child Speech

**معرفگی، جانداری و درونداد: شکل‌گیری نشانه‌گذاری تمایزی مفعول در گفتار کودکان فارسی‌زبان**

Samaneh Soltanabadi & Vali Rezai — Department of Linguistics, University of Isfahan

## Research questions

1. Among true direct objects in Persian child speech, which factor best predicts the presence of the object marker *rā/ro*: definiteness, specificity, animacy, or NP type?
2. Does each child's marking pattern match the pattern in her own caregivers' input (same recording sessions)?
3. Does the marking pattern change with age within each child?
4. How do child and caregiver patterns compare with adult written Persian (PerDT)?

## Data

| Source | Description | Location |
|---|---|---|
| Family corpus (CHILDES/TalkBank) | Two Persian-speaking children, Lilia (1;11–2;10) and Minu (4;0–5;2), plus caregiver speech. doi:10.21415/T57K50 | `data/raw/` (not redistributed; download from TalkBank) |
| UD Persian-PerDT | Adult written Persian, dependency-annotated | `data/perdt/` |

Raw CHILDES files are not included in this repository, in line with TalkBank ground rules. Download the Family corpus from https://childes.talkbank.org and place the `.cha` files under `data/raw/Lilia/` and `data/raw/Minu/`.

## Repository structure

```
data/
  raw/          CHAT files of the Family corpus (git-ignored)
  perdt/        PerDT extraction
  annotation/   Excel files for manual annotation
  processed/    Final analysis-ready datasets
codes/          Scripts, prefixed with their two-digit run order (01-, 02-, ...)
results/
  tables/
  figures/
paper/          Manuscript drafts
```

## Pipeline

Scripts in `codes/` are run in numerical order. Each script lists its inputs and outputs at the top.

| Step | Script | Purpose |
|---|---|---|
| 01 | `01-inspect_corpus.py` | Report speakers, utterance counts and age ranges per file |
| 02 | `02-inspect_tiers.py` | Show examples of dependent tiers (%xmor, %xcau, ...) and %xmor tag frequencies |
| 03 | `03-parse_xmor.py` | Parse %xmor into utterance and token tables; report rā/ro markers and their hosts |
| … | … | (added as the project proceeds) |

## Annotation scheme (summary)

Each candidate NP is coded for: direct-object status, *rā/ro* marking, definiteness (definite / indefinite-specific / indefinite-nonspecific / generic), animacy (human / animal / inanimate), NP type, verb, and whether the utterance is an imitation or formulaic chunk. About 20% of the data is double-coded; inter-annotator agreement is reported as Cohen's kappa.

## Requirements

```
pip install -r requirements.txt
```

## Citation

Data: Family, N. (2009). Lighten up: The acquisition of light verb constructions in Persian. *Proceedings of BUCLD 33*, 139–150. MacWhinney, B. (2000). *The CHILDES Project*. Lawrence Erlbaum.
