# 我的部分：Embedding 与多路召回（Maple）

英文版：[README_MapleEMBEDDINGandSEARCH.md](README_MapleEMBEDDINGandSEARCH.md)

## 完成了什么

对应项目分工里的第 4、5 步：

4. **Embedding**：给数据库里每篇论文生成向量表示（每篇一份）。
5. **搜索**：输入一个自然语言问题，返回最相关的 top-k 篇论文；另外支持"找相似论文"，以及没有相关结果时推荐论文。

已经在本地数据库上用 1000 篇论文（和 Juliette 语料相同的 OpenAlex 筛选条件）完整测试通过。完整的 25000 篇要等导入 dump 后再做 embedding。

## 整体流程

```
 ┌──────────── Juliette ────────────┐     ┌──────────────────── Maple ─────────────────────┐     ┌── Yasir / Katya ──┐
 works, authors, work_authors  ───────►  build_index.py  ──►  search_index 表
                                                                      │
                          用户的问题  ────────────────►  search(query, k)  ──►  top-k 论文  ───►  API  ──►  网站
                          某篇论文 id ────────────────►  similar_works(id) ──►  相似论文
```

## 第一部分：Embedding（`search/build_index.py`）

**做什么：** 读取每篇论文，把文字转换成能表示含义的数字（向量）存起来，搜索时用来和问题做比较。

**输入：** Juliette 的 `works` 表中的 `id`、`title`、`abstract`。
每篇论文被 embed 的文本是 `标题 + 换行 + 摘要`（最多 512 个 token）。

**模型：** [BGE-M3](https://huggingface.co/BAAI/bge-m3)，免费，在本机运行，不需要 API key。
模型算一次同时得到两种向量：

| 表示 | 是什么 | 擅长 |
|---|---|---|
| 稠密向量（dense） | 1024 个数字，表示整段文字的含义 | 同义词、换种说法表达同一个意思 |
| 稀疏向量（sparse） | 文中每个重要词的权重 | 精确的关键术语 |

**输出：** 新表 `search_index`（由 `database/sql/002_search_index.sql` 创建），每篇论文一行：

| 列 | 内容 |
|---|---|
| `work_id` | 等于 `works.id`（例如 `W2741809807`） |
| `dense` | 稠密向量，`vector(1024)`（pgvector） |
| `sparse` | 稀疏向量，`sparsevec(250002)`（pgvector） |
| `tsv` | PostgreSQL 全文检索格式的标题（权重 A）+ 摘要（权重 B） |
| `model`、`text_hash` | 用了哪个模型、对哪段文本做的 embedding，用来判断是否需要重新计算 |
| `updated_at` | embedding 的时间 |

向量用 HNSW 索引，全文用 GIN 索引，让检索更快。

这张表特意和 `works` 分开：重新导入 works 的 dump 不会删掉 embedding，重新做 embedding 也不会改动 Juliette 的表。

**注意**
- 可以续跑：再次运行只处理新增的论文，或者标题、摘要改过的论文。
- 速度：笔记本 GPU（RTX 4060）上约每秒 18 篇，25000 篇大约 23 分钟；CPU 上会慢很多。
- 只需要一个人跑：跑完后导出 dump，其他人导入就有 embedding 了。

## 第二部分：多路召回搜索（`search/retriever.py`）

**做什么：** 用三种不同方式（三"路"）分别找和问题相关的论文，再把三份结果合并成一个排序。

**输入：**
- 用户的自然语言问题，例如 `"graph neural networks for drug discovery"`
- `k`：返回几篇（默认 10）
- 可选：`year_from`、`year_to`（按发表年份过滤）

**过程：**

1. 用和论文**相同**的模型，把问题转成稠密向量和稀疏向量。
2. 三路各自返回最好的 100 篇候选：

   | 路 | 比较方式 | 能找到 |
   |---|---|---|
   | dense | 稠密向量的余弦相似度 | 意思相同的论文 |
   | sparse | 稀疏向量的内积 | 有相同重要词的论文 |
   | keyword | PostgreSQL 全文检索（问题里任意一个词能匹配就算，标题匹配权重更高） | 精确术语、缩写、人名 |

3. **融合（RRF，倒数排名融合）**：每篇论文的得分 = `Σ 1 / (60 + 它在每一路中的排名)`。被多路同时排在前面的论文得分最高。RRF 只用排名，所以三路分数的量纲不同也没关系。
4. 可选的 **rerank（精排）**：用第二个模型（bge-reranker-v2-m3）把问题和前 50 篇论文逐篇一起读，重新排序。更准，但更慢。默认关闭，还没有测试。
5. 从 Juliette 的表里读取 top-k 论文的元数据和作者。

**输出：** 一个字典（可以直接转成 JSON）：

```
{
  "query": "graph neural networks for drug discovery",
  "results": [ top-k 篇论文，最相关的在前 ],
  "low_confidence": false,      没有论文和问题真正接近时为 true
  "suggestions": [],            low_confidence 为 true 时给出的高被引论文推荐（FR-05）
  "best_similarity": 0.68,      dense 路的最高余弦相似度
  "candidates": {"dense": 100, "sparse": 100, "keyword": 100},
  "timing_ms": {...}
}
```

`results` 里每篇论文包含：

```
rank, score, work_id, title, abstract, publication_year, cited_by_count, doi, type,
landing_page_url, pdf_url,
authors: [{id, name, affiliation, position}, ...]       按作者顺序，1 = 第一作者
routes:  {"dense": {"rank": 3, "score": 0.71}, "keyword": {...}}   被哪几路找到、排第几
```

`score` 只是排序用的分数，不是"相关的概率"。

**其他函数：**

| 函数 | 输入 | 输出 | 对应需求 |
|---|---|---|---|
| `similar_works(work_id, k)` | 一篇论文的 id | 和它最相近的 k 篇（dense + sparse 两路，RRF 融合） | FR-05 "找相似论文" |
| `popular_works(k)` | — | 被引次数最高的 k 篇 | FR-05 推荐 |

给 API 用的完整说明（参数、`.env` 里的设置）：[`search/README.md`](../search/README.md)。

## 测试结果（1000 篇）

| 测试 | 结果 |
|---|---|
| `"BERT pre-training of language models"` | 返回预训练语言模型相关论文，三路都命中 |
| `"graph neural networks"`，限定 2021–2022 年 | 只返回 2022 年的 GNN 综述（过滤生效） |
| `"chocolate cake recipe"` / `"how to grow tomatoes"` | 最高相似度 0.33 / 0.38 → 判为 `low_confidence` 并返回推荐 |
| 单次搜索速度（模型已加载） | 问题编码约 50 ms + 三路召回约 60 ms |
| 启动后第一次搜索 | 多约 25 秒（只在第一次加载模型） |
| 已知条目测试（用标题当问题，200 篇） | 每次都在前 10 名；融合后的 MRR 最高（0.998） |

已知条目测试在 1000 篇上太容易，看不出各路的差别；等 25000 篇数据到了再跑一次，用来调各路权重。

## 如何运行

1. 启动数据库并导入论文（见 Juliette 的说明）。
2. 安装：先装 PyTorch（有 NVIDIA 显卡就装 CUDA 版，见 pytorch.org），然后 `%pip install -r requirements.txt`。需要 Python ≥ 3.10。
3. 运行 `search/build_index.py`（第一次会下载模型，约 2.3 GB）。
4. 运行 `search/search_demo.py`，改文件开头的 `QUERY` 试别的问题。
5. 可选：运行 `search/evaluate.py` 比较各路效果。

模型下载慢或连不上时，在 `.env` 里加 `HF_ENDPOINT=https://hf-mirror.com`。

## 文件

| 文件 | 作用 |
|---|---|
| `database/sql/002_search_index.sql` | 创建 `search_index` 表和索引 |
| `search/config.py` | 设置（模型、候选数量、各路权重、阈值） |
| `search/embedder.py` | 加载 BGE-M3，把文字转成稠密 + 稀疏向量；reranker |
| `search/setup_schema.py` | 在已有数据库里创建 `search_index` |
| `search/build_index.py` | 第一部分：给论文做 embedding |
| `search/retriever.py` | 第二部分：`search`、`similar_works`、`popular_works` |
| `search/search_demo.py` | 试搜索 |
| `search/evaluate.py` | 比较各路效果 |

## 待办

- 导入 25000 篇的 dump，全部做 embedding，再导出包含 embedding 的新 dump。
- 在完整语料上调各路权重和 `low_confidence` 阈值（目前是 0.40）。
- 测试 reranker，决定是否默认开启。
- keyword 路用的是 PostgreSQL 的 `ts_rank`，效果接近 BM25，但不是严格的 BM25。
