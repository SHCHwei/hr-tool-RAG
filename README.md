# hr-tool-RAG

專案緣由是因為做了工具 hr-tool[https://github.com/SHCHwei/hr-tool]，整理出完整的規則，就順便延伸做出RAG。  
資料庫是使用 mongodb/mongodb-atlas-local:preview，未來有時間再嘗試其他向量資料庫。




## 設定說明


### 設定 OpenAI API KEY
```
export OPENAI_API_KEY=sk-...
```

### 啟用 docker 建立 DB
```
docker compose up -d
```