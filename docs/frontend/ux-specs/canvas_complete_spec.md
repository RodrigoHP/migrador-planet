
# Document Template Editor — Canvas Specification

## Purpose

This document specifies the **Canvas subsystem** of the Document Template Editor.

The Canvas is the **central visual workspace** where the operator views and edits the document template.

This specification consolidates all UX, UI, and technical agreements defined during architecture design.

The goal is to define the Canvas in sufficient detail so that an AI developer (Claude Code or similar)
can implement it correctly.

---

# 1. Canvas Overview

The Canvas is the main visual surface of the editor.

It renders the **actual document template as HTML** and allows the user to interact with the layout.

Important rule:

The Canvas always renders the **real final document**.

This means:

- No wireframes
- No placeholder boxes
- No simulated layout

The document shown in the Canvas is the **same HTML that will be used to generate the final PDF.**

---

# 2. Canvas Rendering Architecture

Rendering pipeline:

template.json
↓
HTML Template Generator
↓
HTML + CSS + Knockout bindings
↓
Canvas iframe
↓
Rendered document

The Canvas itself does not generate layouts.

It only **renders the generated HTML**.

---

# 3. Canvas Container Architecture

The Canvas is implemented as an iframe to ensure layout isolation.

Editor layout:

Toolbar
Structure Tree | Canvas iframe
Inspector

The Canvas container:

<Canvas>
   <iframe id="document-canvas"></iframe>
</Canvas>

The iframe isolates:

- CSS
- fonts
- layout rules
- document styling

This prevents document CSS from interfering with the editor UI.

---

# 4. Canvas HTML Structure

The HTML loaded inside the iframe follows a standardized structure.

<html>
<head>
  <style>
    /* Generated CSS */
  </style>
</head>

<body>

<header>
  Document header
</header>

<main>
  Flow content (tables, text, blocks)
</main>

<footer>
  Page footer
</footer>

</body>
</html>

---

# 5. Canvas Rendering Flow

When opening a template:

1. Load template.zip
2. Extract template.json
3. Run HTML Generator
4. Produce HTML document
5. Inject HTML into iframe

Pseudo implementation:

iframe.srcdoc = generatedHTML

---

# 6. Canvas Interaction Model

The Canvas supports direct interaction with document elements.

Supported interactions:

Selection
Dragging
Resizing
Inspection

---

# 7. Element Selection

When the user clicks an element in the Canvas:

1. Click event is captured
2. Element identifier is detected
3. Editor selects element
4. Inspector panel displays properties

Selected elements are highlighted visually.

Example highlight:

border: 1px solid blue

---

# 8. Dragging Elements

Elements can be repositioned directly inside the Canvas.

Interaction flow:

User drags element
↓
Editor updates template.json
↓
HTML generator runs
↓
Canvas re-renders

---

# 9. Resizing Elements

Resizable elements expose resize handles.

Supported resize types:

Text blocks
Images
Tables
Containers

Resize modifies layout properties stored in template.json.

---

# 10. Canvas Scrolling

Documents can exceed viewport height.

Canvas therefore supports vertical scrolling.

Scrolling occurs inside the iframe.

The editor container itself does not scroll the document.

---

# 11. Multi Page Visualization

Documents may contain multiple pages.

Pages are displayed vertically.

Example:

Page 1
Page 2
Page 3

Each page appears as a separate visual block.

---

# 12. Handling Large Documents

Documents may contain many pages (100+).

For MVP:

Render all pages normally.

Future optimization:

Virtual page rendering.

---

# 13. Canvas Zoom

Zoom controls allow the operator to change viewing scale.

Possible zoom levels:

50%
75%
100%
125%

Zoom applies CSS transform scaling to the iframe container.

---

# 14. Canvas State Management

The Canvas does not store document state.

All persistent state lives in:

template.json

Canvas only holds:

Rendered HTML
Temporary selection state

---

# 15. Canvas Performance Model

The MVP uses full re-render strategy.

Editing flow:

User modifies layout
↓
template.json updates
↓
HTML regenerated
↓
iframe content replaced

This is simpler and reduces implementation complexity.

---

# 16. Canvas Responsibilities

The Canvas is responsible for:

Rendering document HTML
Displaying pages
Allowing element selection
Allowing drag interactions
Allowing resize interactions
Visual feedback for selection

---

# 17. Canvas Non Responsibilities

The Canvas does NOT:

Store template state
Run document pipeline
Generate templates
Manage schema mapping

---

# 18. Canvas Visual Consistency

Because the Canvas renders the real HTML, the following rule applies:

What the user sees in the Canvas
=
What the final document generator produces.

This ensures WYSIWYG behavior.

---

# 19. Canvas Security Isolation

The iframe also ensures safe isolation of:

CSS resets
Document fonts
Page break rules

---

# 20. Final Canvas Definition

The Canvas is defined as:

An iframe-based rendering surface that displays the generated HTML template,
allowing interactive selection and manipulation of document layout elements.

