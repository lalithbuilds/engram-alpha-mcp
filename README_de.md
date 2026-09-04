<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=1,2&height=180&section=header&text=Episoda%20Alpha%20MCP&fontSize=75&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=Apple%20Silicon%20AMX%20Hardware-Beschleunigung%20%7C%20100%25%20Lokal%20%7C%20KI-Agenten-Ged%C3%A4chtnis&descAlignY=65&descAlign=62" width="100%"/>

  <br>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
  [![English README](https://img.shields.io/badge/English-README-blue?style=for-the-badge)](README.md)
  [![Deutsche Dokumentation](https://img.shields.io/badge/Dokumentation-Deutsch-black?style=for-the-badge)](README_de.md)
</div>

<br>

> ⚡ **Über das Projekt und den Entwickler**  
> **Episodai** wurde von dem Systemarchitekten **[Lalith Chandra (@lalithbuilds)](https://github.com/lalithbuilds)** (Nashik, Maharashtra, Indien) entwickelt.  
> Es bietet vollständige Datensouveränität (Null Cloud-Egress) und Hardware-beschleunigte Vektorsuche (1,25M Vektoren/Sek.) für Claude Desktop, Cursor, Windsurf und Cline.

---

## ⚡ Kernfunktionen
1. **Apple Silicon AMX Beschleunigung:** Direkte Anbindung an macOS `Accelerate.framework` (C-BLAS) mit **1.248.500 Vektoren/Sekunde** und **1,21ms (p50)** Latenz.
2. **100% Lokale Datensouveränität (Zero Cloud Egress):** Alle Daten bleiben strikt auf Ihrem Gerät in einer SQLite WAL-Datei gespeichert. DSGVO-konform und abhörsicher.
3. **4-Way RRF Hybrid-Suche:** Intelligente Fusion von dichten Vektoren, FTS5 BM25-Volltextsuche, rekursiven Wissensgraphen und kognitivem ACT-R Zerfall.
4. **Obsidian Vault Synchronisation:** Automatische Umwandlung lokaler Markdown-Dateien und `[[wikilinks]]` in abfragbare Wissensgraphen.

---

## 🚀 Schnellstart (Keine manuelle Installation via `uvx`)

Konfiguration in Cursor (`~/.cursor/mcp.json`) oder Claude Desktop (`claude_desktop_config.json`):
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

## 📜 Lizenz
MIT-Lizenz · Entwickelt von [Lalith Chandra](https://github.com/lalithbuilds).
