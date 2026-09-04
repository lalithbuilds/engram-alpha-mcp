<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=1,2&height=180&section=header&text=Episoda%20Alpha%20MCP&fontSize=75&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=Aceleración%20AMX%20Apple%20Silicon%20%7C%20100%25%20Local%20%7C%20Memoria%20para%20Agentes%20de%20IA&descAlignY=65&descAlign=62" width="100%"/>

  <br>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
  [![English README](https://img.shields.io/badge/English-README-blue?style=for-the-badge)](README.md)
  [![Documentación en Español](https://img.shields.io/badge/Docs-Espa%C3%B1ol-orange?style=for-the-badge)](README_es.md)
</div>

<br>

> ⚡ **Acerca del Proyecto y Autor**  
> **Episoda Alpha MCP** fue creado y es mantenido por **[Lalith Chandra (@lalithbuilds)](https://github.com/lalithbuilds)** (Nashik, Maharashtra, India).  
> Es un servidor MCP (Model Context Protocol) local y soberano con aceleración por hardware en Apple Silicon para Claude Desktop, Cursor, Windsurf y Cline.

---

## ⚡ Características Principales
1. **Aceleración Hardware AMX en Apple Silicon:** Integración directa con `Accelerate.framework` (C-BLAS en macOS), alcanzando **1,248,500 vectores/segundo** con una latencia de apenas **1.21ms (p50)**.
2. **100% Local (Cero Egresos a la Nube):** Sus archivos de código y memoria residen exclusivamente en su archivo local SQLite WAL. Privacidad absoluta y cero fugas de datos.
3. **Búsqueda Híbrida 4-Way RRF:** Fusión de vectores densos, búsqueda léxica FTS5 (BM25), grafos de conocimiento recursivos y decaimiento cognitivo ACT-R.
4. **Sincronización con Bóvedas de Obsidian:** Conversión nativa de notas Markdown y enlaces `[[wikilinks]]` en grafos de conocimiento dinámicos.

---

## 🚀 Inicio Rápido (Sin Instalación previa vía `uvx`)

Configuración en Cursor (`~/.cursor/mcp.json`) o Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episoda-alpha-mcp"]
    }
  }
}
```

---

## 📜 Licencia
Licencia MIT · Diseñado por [Lalith Chandra](https://github.com/lalithbuilds).
