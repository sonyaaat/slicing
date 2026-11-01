import pandas as pd
from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0  # детермінований результат

FILE_GPT = "/Users/sofi/Desktop/uni/1/gpt55_results_full.csv"
FILE_CLAUDE = "/Users/sofi/Desktop/uni/1/claude_opus47_results_full.csv"

OUT_GPT_MATCHED = "/Users/sofi/Desktop/uni/1/gpt55_matched.csv"
OUT_CLAUDE_MATCHED = "/Users/sofi/Desktop/uni/1/claude_opus47_matched.csv"
OUT_GPT_MATCHED_EN = "/Users/sofi/Desktop/uni/1/gpt55_matched_en.csv"
OUT_CLAUDE_MATCHED_EN = "/Users/sofi/Desktop/uni/1/claude_opus47_matched_en.csv"

df_gpt = pd.read_csv(FILE_GPT)
df_claude = pd.read_csv(FILE_CLAUDE)

print("=" * 70)
print("ВИХІДНІ РОЗМІРИ")
print("=" * 70)
print("GPT-5.5:", df_gpt.shape)
print("Claude Opus 4.7:", df_claude.shape)

# --- Крок 1: знайти проблемні prompt_id (порожня completion) в ОБОХ датасетах ---
def empty_mask(df):
    return df["completion"].isna() | (df["completion"].astype(str).str.strip() == "")

problematic_gpt = set(df_gpt.loc[empty_mask(df_gpt), "prompt_id"])
problematic_claude = set(df_claude.loc[empty_mask(df_claude), "prompt_id"])
problematic_ids = problematic_gpt | problematic_claude

print("\n" + "=" * 70)
print("КРОК 1 — ВИКЛЮЧЕННЯ ПРОБЛЕМНИХ PROMPT_ID (немає completion)")
print("=" * 70)
print("Проблемні в GPT:", len(problematic_gpt))
print("Проблемні в Claude:", len(problematic_claude))
print("Всього унікальних проблемних prompt_id (об'єднання):", len(problematic_ids))

df_gpt_clean = df_gpt[~df_gpt["prompt_id"].isin(problematic_ids)].copy()
df_claude_clean = df_claude[~df_claude["prompt_id"].isin(problematic_ids)].copy()

print("\nПісля виключення:")
print("  GPT clean:", df_gpt_clean.shape)
print("  Claude clean:", df_claude_clean.shape)
print("  Розміри однакові?", df_gpt_clean.shape[0] == df_claude_clean.shape[0])

# --- Звірка: prompt_id та тексти питань співпадають між очищеними датасетами ---
ids_gpt_clean = set(df_gpt_clean["prompt_id"])
ids_claude_clean = set(df_claude_clean["prompt_id"])
print("  Однакові набори prompt_id?", ids_gpt_clean == ids_claude_clean)

merged_check = df_gpt_clean[["prompt_id", "question"]].merge(
    df_claude_clean[["prompt_id", "question"]], on="prompt_id", suffixes=("_gpt", "_claude")
)
merged_check["match"] = merged_check["question_gpt"] == merged_check["question_claude"]
print("  Тексти питань співпадають дослівно:", merged_check["match"].sum(), "/", len(merged_check))

# Зберігаємо у стабільному порядку за prompt_id для відтворюваності
df_gpt_clean = df_gpt_clean.sort_values("prompt_id").reset_index(drop=True)
df_claude_clean = df_claude_clean.sort_values("prompt_id").reset_index(drop=True)

df_gpt_clean.to_csv(OUT_GPT_MATCHED, index=False)
df_claude_clean.to_csv(OUT_CLAUDE_MATCHED, index=False)

# --- Крок 2: фільтр лише англомовних питань (синхронно для обох) ---
print("\n" + "=" * 70)
print("КРОК 2 — ФІЛЬТР ЛИШЕ АНГЛОМОВНИХ ПИТАНЬ")
print("=" * 70)

def is_english(text):
    if not isinstance(text, str) or not text.strip():
        return False
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False

# Мова визначається по тексту питання — він однаковий для обох моделей,
# тож рахуємо один раз на базовому наборі question -> prompt_id
question_lang = df_gpt_clean[["prompt_id", "question"]].copy()
question_lang["is_en"] = question_lang["question"].apply(is_english)

en_ids = set(question_lang.loc[question_lang["is_en"], "prompt_id"])
non_en_ids = set(question_lang.loc[~question_lang["is_en"], "prompt_id"])

print("Всього питань (після виключення проблемних):", len(question_lang))
print("Англомовних:", len(en_ids))
print("Не англомовних (виключено):", len(non_en_ids))

df_gpt_matched_en = df_gpt_clean[df_gpt_clean["prompt_id"].isin(en_ids)].copy()
df_claude_matched_en = df_claude_clean[df_claude_clean["prompt_id"].isin(en_ids)].copy()

df_gpt_matched_en = df_gpt_matched_en.sort_values("prompt_id").reset_index(drop=True)
df_claude_matched_en = df_claude_matched_en.sort_values("prompt_id").reset_index(drop=True)

df_gpt_matched_en.to_csv(OUT_GPT_MATCHED_EN, index=False)
df_claude_matched_en.to_csv(OUT_CLAUDE_MATCHED_EN, index=False)

# --- ЗВІТ ---
print("\n" + "=" * 70)
print("ФІНАЛЬНИЙ ЗВІТ ЗВІРКИ")
print("=" * 70)

print("\n1) Набір 'усі з відповіддю' (matched, без 35 проблемних):")
print("   ", OUT_GPT_MATCHED, "->", df_gpt_clean.shape)
print("   ", OUT_CLAUDE_MATCHED, "->", df_claude_clean.shape)
print("    Розміри рівні:", df_gpt_clean.shape == df_claude_clean.shape)
print("    prompt_id набори ідентичні:", set(df_gpt_clean.prompt_id) == set(df_claude_clean.prompt_id))

print("\n2) Набір 'лише англомовні' (matched + EN-фільтр):")
print("   ", OUT_GPT_MATCHED_EN, "->", df_gpt_matched_en.shape)
print("   ", OUT_CLAUDE_MATCHED_EN, "->", df_claude_matched_en.shape)
print("    Розміри рівні:", df_gpt_matched_en.shape == df_claude_matched_en.shape)
print("    prompt_id набори ідентичні:", set(df_gpt_matched_en.prompt_id) == set(df_claude_matched_en.prompt_id))

# Повна звірка текстів питань у фінальному EN-наборі (рядок-в-рядок після сортування за prompt_id)
texts_equal = (df_gpt_matched_en["prompt_id"].values == df_claude_matched_en["prompt_id"].values).all() and \
              (df_gpt_matched_en["question"].values == df_claude_matched_en["question"].values).all()
print("    prompt_id та question ідентичні рядок-в-рядок після сортування:", texts_equal)

n_mismatch_ids = (df_gpt_matched_en["prompt_id"].values != df_claude_matched_en["prompt_id"].values).sum()
n_mismatch_text = (df_gpt_matched_en["question"].values != df_claude_matched_en["question"].values).sum()
print("    Розбіжностей у prompt_id:", n_mismatch_ids)
print("    Розбіжностей у тексті питання:", n_mismatch_text)

print("\nПідсумкові розміри для аналізу:")
print(f"  Набір 1 (усі з відповіддю, обидві мови): {df_gpt_clean.shape[0]} прикладів на модель")
print(f"  Набір 2 (лише англомовні):               {df_gpt_matched_en.shape[0]} прикладів на модель")
