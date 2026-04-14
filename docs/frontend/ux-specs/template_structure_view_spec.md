
# Template Structure View — Layout Structure Specification

## Overview

The **Template Structure View** is a UI component of the Template Editor that displays
the logical hierarchy of the document layout.

Unlike the visual canvas (PDF viewer), this panel shows the **structural representation**
of the template elements.

This helps users:

- navigate complex templates
- select elements precisely
- understand document hierarchy
- manage pagination regions
- visualize anchors and flow behavior

---

# Goals

The Layout Structure View provides:

1. Structural navigation
2. Precise element selection
3. Document hierarchy visualization
4. Flow layout understanding
5. Element reordering capabilities

---

# Placement in the UI

The Structure View appears in the **left sidebar of the editor**.

Example layout:

Toolbar
Structure Panel | Canvas | Inspector Panel

---

# Example UI Wireframe

Template Structure Panel

Document
 ├ Header
 │   ├ Logo
 │   ├ Cliente
 │   └ CPF
 │
 ├ Flow
 │   ├ Table movimentos
 │   │   ├ descricao
 │   │   ├ valor
 │   │   └ data
 │   │
 │   └ Chart vendas
 │
 └ Footer
     └ Page Number

---

# Core Hierarchy Model

The document is represented as a tree.

Root
 └ Document
     ├ Header
     ├ Flow
     └ Footer

Each node can contain child elements.

---

# Root Node

Document

The root represents the template.

Properties:

template_id  
template_name  
page_settings  

---

# Header Section

The header region contains elements that repeat on every page.

Typical elements:

logo  
document title  
customer information  

Example:

Header
 ├ Logo
 ├ Cliente
 └ CPF

Properties:

repeat_each_page = true

---

# Flow Section

The flow section contains content that expands and triggers pagination.

Typical elements:

tables  
charts  
paragraphs  

Example:

Flow
 └ Table movimentos

Properties:

paginated = true

---

# Footer Section

Footer elements repeat on every page.

Example:

Footer
 └ Page Number

Properties:

repeat_each_page = true

---

# Element Types

Supported node types include:

Text  
Image  
Table  
Chart  
Container  

Each type has unique configuration options.

---

# Icons in Structure View

Icons help identify element types.

📄 Document  
📦 Container  
🔤 Text  
📋 Table  
📊 Chart  
🖼 Image  

---

# Element Selection

Clicking a node selects the element in the canvas.

Example:

User clicks:

Table movimentos

Result:

Canvas highlights the table.

Inspector panel loads its properties.

---

# Element Highlighting

When an element is selected in the structure tree:

The canvas visually highlights the corresponding element.

This improves navigation in large templates.

---

# Drag and Drop Reordering

Elements can be reordered via drag-and-drop.

Example:

Flow
 ├ Chart vendas
 └ Table movimentos

User drags chart above table.

---

# Anchor Visualization

Each element displays its layout anchor.

Examples:

Header (Top Anchor)

Flow elements (Flow Anchor)

Footer (Bottom Anchor)

This helps users understand pagination behavior.

---

# Optional Element Indicators

Elements that appear only in some document variants are marked as optional.

Example:

Telefone (Optional)

These are derived from the Layout Variants Explorer.

---

# Binding Display

The structure view may display bindings.

Example:

Cliente → {{cliente}}

CPF → {{cpf}}

Table movimentos → {{movimentos}}

This provides quick visibility into data connections.

---

# Integration with Other Panels

The Structure View integrates with:

Canvas Viewer  
Element Inspector  
Layout Variants Explorer  
Validation Console  

Selecting a node updates all panels.

---

# Example Complete Structure

Document
 ├ Header
 │   ├ Logo
 │   ├ Cliente → {{cliente}}
 │   └ CPF → {{cpf}}
 │
 ├ Flow
 │   ├ Table movimentos → {{movimentos}}
 │   │   ├ descricao
 │   │   ├ valor
 │   │   └ data
 │   │
 │   └ Chart vendas → {{vendasMensais}}
 │
 └ Footer
     └ Page Number

---

# Benefits

The Template Structure View enables:

faster navigation  
clear hierarchy visualization  
better debugging of layouts  
precise element selection  
better understanding of pagination  

---

# Summary

The Layout Structure View is an essential tool for managing complex document templates.

It provides a hierarchical representation of:

Header  
Flow Content  
Footer  

and all nested elements.

This allows users to manage document layouts more effectively than relying on visual editing alone.
