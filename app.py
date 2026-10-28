from openai import OpenAI
from mongodb import connect_to_mongodb


client = OpenAI()
database = connect_to_mongodb()

print(f"database: {database}")

collection = database["hrtool"]


EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
MIN_SCORE = 0.7

SYSTEM_PROMPT = """你是公司考勤規則的問答助理。
只能根據【參考資料】回答，不可使用外部知識或臆測。
若資料不足以回答，請回答「目前資料庫中找不到相關規則」。
回答使用繁體中文（台灣），簡潔明確，並在句末標註引用來源，例如 [1][2]。"""


def search(query_emb, k=3):
    """執行 Atlas $vectorSearch，查詢失敗時將例外直接傳回呼叫端。"""
    return list(collection.aggregate([
        {"$vectorSearch": {
            "index": "vector_index",
            "path": "embedding",
            "queryVector": query_emb,
            "numCandidates": 100,
            "limit": k,
        }},
        {"$project": {"_id": 0, "content": 1, "score": {"$meta": "vectorSearchScore"}}},
    ]))



def answer(question, results):
    """依檢索結果以串流方式產生自然語言回答。"""
    hits = [r for r in results if r["score"] >= MIN_SCORE]
    if not hits:
        print("目前資料庫中找不到相關規則。")
        return "目前資料庫中找不到相關規則。"

    context = "\n".join(f"[{i}] {r['content']}" for i, r in enumerate(hits, 1))
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.1,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"【參考資料】\n{context}\n\n【問題】{question}"},
        ],
    )
    text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or "" if chunk.choices else ""
        print(delta, end="", flush=True)
        text += delta
    print()
    return text


while True:
    question = input("你：").strip()

    if question.lower() in {"exit", "quit", "離開"}:
        break

    emb = client.embeddings.create(model=EMBED_MODEL, input=question).data[0].embedding

    results = search(emb)

    print("\n【檢索結果】")
    for r in results:
        print(f"[{r['score']:.4f}] {r['content']}")

    print("\n【回答】")
    answer(question, results)
    print()



    
