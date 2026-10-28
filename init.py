import time

from openai import OpenAI
from pymongo.operations import SearchIndexModel

from mongodb import connect_to_mongodb

EMBED_MODEL = "text-embedding-3-small"
INDEX_NAME = "vector_index"

DOCS = [
    "平日加班包含首次上班早於 workStart 的時間，以及各出勤時段中晚於 workOff + 15 分鐘 的工作時間。",
    "平日早退與下班後加班使用員工設定的下班基準時間，未提供有效設定時預設為 17:30。週末則採不同計算方式。",
    "考勤基準時間參考以下三點,1.上班基準時間 (workStart)：基準時間點依員工設定，首次上班早於此時間的差額計入平日加班,晚於此時間則計算遲到 2.下班基準時間 (workOff):預設 17:30,平日早退判定基準,可由員工設定取代 3.加班起算時間 (workOver):workOff + 15 分鐘，平日有效下班時間晚於此時間時計入下班後加班,預設為 17:45",
    "早退時數判定條件：平日有效下班時間早於設定的 workOff（預設 17:30）",
    "加班時數判定條件：平日首次上班早於 workStart，或任一出勤時段超過 workOff + 15 分鐘（預設 17:45）",
    "正常下班緩衝區間判定區間：workOff <= 有效下班時間 <= workOff + 15 分鐘（預設 17:30 至 17:45）",
    "跨夜 (次日凌晨) 下班規則判定條件：平日有效下班時間的小時數小於 6，即 00:00 至 05:59",
    "週末出勤加班判定條件：星期六或星期日有完整的上、下班打卡區間",
    "雙段出勤：若有填寫「二次上班」，首次下班與二次上班至二次下班作為分開的出勤段計算加班；若二次下班未填，仍計算首次下班段及提早上班加班，但不計二次出勤段或早退。",
    "單段出勤：若未填寫「二次上班」，優先取「二次下班」；若無則取「首次下班」（如僅上午出勤半天，或全天僅打兩次卡）。",
    "未打卡/放假：平日沒有有效下班打卡時，不計算下班後加班與早退；若首次上班早於 workStart，仍依新增規則計入提前上班加班。週末則只加總完整的上、下班區間。",
    "遲到時數判定條件：首次上班打卡晚於員工設定的上班基準時間",
]


def wait_for_mongodb(retries=30, delay=2):
    """等待 MongoDB 就緒。"""
    """啟動順序問題：compose 的 `depends_on` 只保證 `mongodb` 容器已啟動，不保證 MongoDB 已能接受連線。Atlas Local 啟動較慢，`init` 若立刻連線，會因 `serverSelectionTimeoutMS=5000` 逾時而失敗。"""
    for i in range(retries):
        try:
            return connect_to_mongodb()
        except Exception as e:
            print(f"等待 MongoDB 就緒 ({i + 1}/{retries})：{e}")
            time.sleep(delay)
    raise RuntimeError("無法連線至 MongoDB")


def insert_docs(client, collection):
    """寫入文件與向量；已有資料時略過，避免重啟後重複寫入。"""
    if collection.count_documents({}) > 0:
        print("hrtool 已有資料，略過寫入。")
        return
    for d in DOCS:
        emb = client.embeddings.create(model=EMBED_MODEL, input=d).data[0].embedding
        result = collection.insert_one({"content": d, "embedding": emb})
        print(f"Inserted result: {result.inserted_id}")
    print("Documents inserted successfully.")


def create_index(collection):
    """建立向量索引；已存在時略過。"""
    if any(idx["name"] == INDEX_NAME for idx in collection.list_search_indexes()):
        print("vector_index 已存在，略過建立。")
        return
    collection.create_search_index(SearchIndexModel(
        name=INDEX_NAME,
        type="vectorSearch",
        definition={
            "fields": [
                {"type": "vector", "path": "embedding",
                 "numDimensions": 1536, "similarity": "cosine"},
                {"type": "filter", "path": "metadata.category"},
            ]
        },
    ))
    print("vector_index 建立完成。")


def main():
    database = wait_for_mongodb()
    collection = database["hrtool"]
    insert_docs(OpenAI(), collection)
    create_index(collection)


if __name__ == "__main__":
    main()
