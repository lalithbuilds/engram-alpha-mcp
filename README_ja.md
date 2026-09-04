<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=1,2&height=180&section=header&text=Episoda%20Alpha%20MCP&fontSize=75&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=Apple%20Silicon%20AMX%20ハードウェア高速化%20%7C%20完全ローカル%20%7C%20AIエージェント記憶基盤&descAlignY=65&descAlign=62" width="100%"/>

  <br>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
  [![English README](https://img.shields.io/badge/English-README-blue?style=for-the-badge)](README.md)
  [![中文文档](https://img.shields.io/badge/文档-简体中文-red?style=for-the-badge)](README_zh.md)
</div>

<br>

> ⚡ **開発者とプロジェクト概要**  
> **Episodai** は、インド・ナーシクの独立システムアーキテクト **[Lalith Chandra (@lalithbuilds)](https://github.com/lalithbuilds)** によって設計・開発されたオープンソースソフトウェアです。  
> Claude Desktop、Cursor、Windsurf、Cline などの AI コーディングエージェント向けに、Apple Silicon AMX による超高速ベクトル計算（毎秒120万回以上）と完全なデータ主権（外部送信ゼロ）を提供します。

---

## ⚡ 主な特徴
1. **Apple Silicon AMX ハードウェアアクセラレーション:** macOS の `Accelerate.framework` (C-BLAS) にネイティブ結合し、**毎秒 1,248,500 ベクトル**の計算と **1.21ms (p50)** の低遅延を実現。
2. **完全ローカル・データ送信ゼロ (Zero Cloud Egress):** すべてのデータは単一のローカル SQLite WAL ファイルに保存され、社内機密コードや API キーの外部漏洩リスクを完全に排除。
3. **4-Way RRF (逆順位融合) ハイブリッド検索:** 密ベクトル、FTS5 BM25 全文検索、再帰的ナレッジグラフ、エビングハウス忘却曲線を統合。
4. **Obsidian ネイティブ連携:** Markdown の Frontmatter と `[[wikilinks]]` を自動解析し、知識グラフとして AI に提供。

---

## 🚀 インストール & 設定 (uvx でゼロ設定実行)

Cursor (`~/.cursor/mcp.json`) または Claude Desktop (`claude_desktop_config.json`) に追加：
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

## 📜 ライセンス
MIT License · Developed by [Lalith Chandra](https://github.com/lalithbuilds).
