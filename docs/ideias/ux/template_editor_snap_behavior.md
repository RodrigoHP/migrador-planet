
# Template Editor — Snap Behavior Specification

This document explains the **Snap system** used in the Template Editor.
Snap helps users align elements precisely when building templates from PDFs.

The goal is to preserve the original document layout while making editing easier.

---

# 1. What is Snap

Snap means **automatic alignment**.

When a user moves or resizes an element, the editor automatically aligns it with nearby references.

Possible references:

- grid lines
- edges of elements
- centers of elements
- page margins
- detected columns
- detected layout guides

---

# 2. Example Without Snap

Without Snap alignment:

```
Cliente: João
   CPF: 123456
```

Elements can become slightly misaligned.

---

# 3. Example With Snap

With Snap enabled:

```
Cliente: João
CPF:     123456
```

The editor automatically aligns the elements.

---

# 4. Types of Snap

The editor supports multiple snap modes simultaneously.

---

# 4.1 Grid Snap

Elements align to a visual grid.

Example grid:

```
|----|----|----|
|----|----|----|
|----|----|----|
```

When moving an element, it snaps to grid intersections.

---

# 4.2 Element Snap

Elements snap to the edges of other elements.

Example:

```
Cliente: João
CPF:     123456
Telefone:999999
```

When moving "Telefone", it snaps to the alignment of "Cliente" and "CPF".

---

# 4.3 Column Snap

Columns detected from the PDF layout become snap guides.

Example:

```
[Labels]      [Values]
Cliente       João
CPF           123456
```

Snap keeps labels and values aligned.

---

# 4.4 Margin Snap

Elements snap to page margins.

Example:

```
| margin
| Cliente: João
| CPF: 123456
```

---

# 4.5 Center Snap

Elements snap to vertical or horizontal center.

Common for:

- titles
- logos
- charts

---

# 5. Visual Snap Guides

When Snap activates, guide lines appear.

Vertical guide example:

```
Cliente: João
      │
      │ snap line
CPF: 123456
```

Horizontal guide example:

```
Cliente: João
──────────── snap
CPF: 123456
```

---

# 6. Snap Configuration

Snap can be enabled or disabled in the toolbar.

Example:

```
Snap: ON
```

Snap options may include:

- Snap to Grid
- Snap to Elements
- Snap to Columns
- Snap to Margins

---

# 7. Snap with Multiple Documents

When multiple example PDFs exist:

Doc1  
Doc2  
Doc3  

Snap uses the **average detected layout**.

Example:

Doc1
```
Cliente: João
CPF: 123456
```

Doc2
```
Cliente: João
CPF:123456
```

Snap creates a shared alignment guide.

---

# 8. Snap for Tables

When working with tables:

```
| Produto | Valor |
| Produto | Valor |
```

Snap aligns elements to table columns.

---

# 9. Snap for Charts

Charts can snap to:

- center
- margins
- grid lines

Example:

```
+--------------+
| chart        |
+--------------+
```

---

# 10. Snap with Auto Fix Layout

The "Auto Fix Layout" feature uses Snap to realign elements automatically.

Process:

```
User clicks Auto Fix Layout
↓
Editor analyzes layout
↓
Snap aligns elements
```

---

# 11. Snap When Creating Elements

When adding new fields:

```
Add Field
```

Dragging the field triggers Snap alignment.

---

# 12. Snap Distance Threshold

Snap activates only when the element is close to a guide.

Example:

```
snapThreshold = 8px
```

If the element is within this distance, it snaps.

---

# 13. Smart Snap Using Layout Skeleton

Snap can use the **Layout Skeleton detected from the PDF**.

This includes:

- detected columns
- detected rows
- detected layout regions

This improves alignment accuracy.

---

# 14. Snap Interaction Flow

Typical process:

```
User drags element
↓
Editor checks nearby anchors
↓
If within threshold
↓
Snap line appears
↓
Element aligns
```

---

# 15. Benefits

Snap provides:

- consistent layout
- faster editing
- reduced manual correction
- better reproduction of the original PDF layout
