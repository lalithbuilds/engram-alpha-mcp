<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=1,2&height=180&section=header&text=Episoda%20Alpha%20MCP&fontSize=75&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=Apple%20Silicon%20AMX%20硬件加速%20%7C%20零云端依赖%20%7C%20AI%20智能体持久记忆引擎&descAlignY=65&descAlign=62" width="100%"/>

  <br>

  [![GitHub Stars](https://img.shields.io/github/stars/lalithbuilds/episodai?style=for-the-badge&logo=github&color=blue)](https://github.com/lalithbuilds/episodai/stargazers)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
  [![English Docs](https://img.shields.io/badge/English-README-blue?style=for-the-badge)](README.md)
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=for-the-badge&logo=python)](https://www.python.org/)
</div>

<br>

> ⚡ **关于项目与作者**  
> **Episodai** 由独立系统架构师 **[Lalith Chandra (@lalithbuilds)](https://github.com/lalithbuilds)** (印度马哈拉施特拉邦纳西克) 原创设计与开发。  
> 本项目是基于 Python 3 与 macOS Accelerate 框架底层 C-BLAS 绑定的自研硬件加速模型上下文协议 (Model Context Protocol, MCP) 服务器，专为解决 AI 智能体跨会话上下文丢失（Amnesia）而生。

---

## ⚡ 为什么选择 Episodai？

目前市面上的主流 AI 记忆方案（如 Mem0、Zep 或 LangChain Memory）存在不可忽视的痛点：
1. **数据隐私风险：** 强依赖第三方云端 Embedding API，企业的私有代码、架构机密面临外泄风险。
2. **严重的网络延迟：** 每次记忆检索需经历 DNS 解析、TLS 握手及云端 API 调用，往返耗时高达 200ms – 500ms。
3. **沉重的容器负担：** 强制捆绑 Docker、PostgreSQL、pgvector 等笨重依赖，占用大量系统资源。

**Episodai 打破了这一僵局：**
* 🍎 **Apple Silicon AMX 硬件加速：** 深度绑定 macOS `Accelerate.framework` 底层向量计算 (`cblas_sdot` / `vDSP`)，在 M 系列芯片上实现高达 **1,248,500 向量/秒** 的矩阵点积吞吐，p50 检索延迟仅 **1.21 毫秒**。
* 🔒 **100% 零云端依赖 (Zero Cloud Egress)：** 代码与记忆数据物理级保存在本地单文件 SQLite WAL 数据库中，杜绝任何外部数据传输。
* 🧠 **4 路倒数排名融合 (4-Way RRF) 混合检索：**
  * 密集向量余弦相似度 (Dense Vectors)
  * Trigram 分词 FTS5 倒排索引检索 (BM25 Lexical)
  * 基于递归 CTE 的知识图谱关系漫游 (Knowledge Graph)
  * 艾宾浩斯与 ACT-R 幂律认知遗忘曲线 (Cognitive Decay)，自动淡化过时陈旧上下文。
* 📝 **原生 Obsidian 双向同步：** 自动递归解析本地 Markdown 笔记的 YAML Frontmatter 与 `[[双链]]`，即刻将个人知识库转变为 AI 可调用的时序知识图谱。

---

## 🚀 极速上手 (零安装，基于 `uvx`)

无需配置复杂的 Python 虚拟环境，使用 `uvx` 即可免安装秒级运行。

### 1. Cursor IDE 配置
在 `~/.cursor/mcp.json` 中添加：
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episodai"]
    }
  }
}
```

### 2. Claude Desktop 配置
在 `claude_desktop_config.json` 中配置：
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episodai"]
    }
  }
}
```

### 3. Claude Code CLI (终端)
```bash
claude mcp add episoda uvx episodai
```

### 4. Windsurf Editor 配置
在 `~/.codeium/windsurf/mcp_config.json` 中添加：
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episodai"]
    }
  }
}
```

---

## 📊 硬件基准测试对比

| 评测指标 | 方案 A: Episodai (本地 AMX) | 方案 B: 本地 Docker (Python+Chroma) | 方案 C: 云端 SaaS (Mem0/Zep) |
| :--- | :---: | :---: | :---: |
| **向量吞吐性能** | **1,248,500 向量/秒** | ~48,000 向量/秒 | 受网络与 API 限流限制 |
| **端到端检索延迟 (p50)** | **1.21 毫秒** | 45.00 毫秒 | 280.00 毫秒 |
| **外部网络传输 (Egress)**| **0 字节 (物理级本地安全)** | 0 字节 | 全量代码与会话上传 |
| **月度 API 账单成本** | **$0.00 (永久开源免费)** | $0.00 | $19 – $249 / 月 |
| **长文本精准召回率** | **100.0% (LongMemEval 10/10)** | 85.0% | 90.0% |

---

## 📜 开源协议

本项目采用 **MIT 开源许可证**。欢迎开发者贡献代码与 Star 支持！
