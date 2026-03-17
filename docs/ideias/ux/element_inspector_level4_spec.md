
# Template Editor — Inspector Level 4
# Element Inspector Specification

## Overview

The **Element Inspector** is the most granular configuration layer in the Template Editor.

It allows operators to configure **individual elements** within the document layout.

Typical elements include:

- Text blocks
- Data fields
- Labels
- Inline images
- Icons
- Small decorative elements

While higher inspector levels control global, sectional, or component-level behavior,
the Element Inspector allows **precise control of a single element's appearance and positioning**.

---

# Position in Inspector Hierarchy

Inspector hierarchy:

1. Page Inspector
2. Section Inspector
3. Component Inspector
4. Element Inspector

The Element Inspector is the **lowest and most detailed level** of configuration.

Changes made here affect **only the selected element**.

---

# Where the Element Inspector is Accessed

The Element Inspector is activated when a **specific element** is selected.

There are two ways to access it.

## Method 1 — Structure Tree

Example:

Document
 ├ Header
 │   ├ Cliente
 │   └ CPF
 ├ Flow
 │   └ Table movimentos
 └ Footer

Selecting **Cliente** activates the Element Inspector.

## Method 2 — Canvas

Clicking directly on an element in the canvas also activates the inspector.

Example:

Click text field → Text Element Inspector.

---

# UI Placement

The Element Inspector appears in the **Inspector Panel** on the right side of the editor.

Editor layout:

Toolbar
Structure Tree | Canvas | Inspector Panel

When an element is selected, the Inspector panel shows **Element Settings**.

---

# Element Inspector UI Layout

Example UI:

Element Settings
--------------------------------

Position
X: 120
Y: 80

Size
Width: 200
Height: Auto

--------------------------------

Typography

Font Family: Helvetica
Font Size: 12
Weight: Bold
Style: Normal

Color: #000000

Line Height: 1.4

--------------------------------

Alignment

Left
Center
Right

--------------------------------

Spacing

Padding
Top
Bottom
Left
Right

Margin
Top
Bottom
Left
Right

---

# Position Controls

Position defines the element location within its parent container.

Properties:

X Position
Y Position

Example:

X: 120px
Y: 80px

This determines where the element appears relative to its container.

---

# Size Controls

Defines element dimensions.

Properties:

Width
Height

Example:

Width: 200px
Height: Auto

If height is set to **Auto**, the element expands based on content.

---

# Typography Controls

Text elements include typography settings.

Properties:

Font Family
Font Size
Font Weight
Font Style
Line Height

Example:

Font: Helvetica
Size: 12
Weight: Bold
Line Height: 1.4

These settings override the **default typography defined in Page Inspector**.

---

# Color Controls

Elements may define their own color settings.

Example:

Text Color
#000000

Background Color
Optional

---

# Alignment

Controls horizontal alignment inside the container.

Options:

Left
Center
Right

Example:

Alignment: Left

---

# Padding

Padding defines internal spacing inside the element.

Properties:

Padding Top
Padding Bottom
Padding Left
Padding Right

Example:

Padding Top: 4px
Padding Bottom: 4px

---

# Margin

Margins define spacing between the element and surrounding elements.

Properties:

Margin Top
Margin Bottom
Margin Left
Margin Right

Example:

Margin Bottom: 8px

---

# Visibility Rules

Elements can be conditionally displayed.

Example:

Visible When
telefone exists

Example rule:

if telefone != null → show element

This supports **optional fields detected by the Layout Variants system**.

---

# Data Binding

Fields can bind to data properties.

Example:

Cliente → {{cliente}}
CPF → {{cpf}}

Binding source defines where the element retrieves its value.

---

# Text Behavior

Text elements may support overflow and wrapping behavior.

Options:

Wrap Text
Truncate
Expand Height

Example:

Wrap Text: Enabled

---

# Element Anchors

Elements can be anchored within their parent container.

Examples:

Top Anchor
Center Anchor
Bottom Anchor

Anchors help maintain consistent positioning during layout adjustments.

---

# Interaction Behavior

Selecting an element performs the following actions:

1. Highlights the element in the canvas
2. Opens the Element Inspector
3. Displays editable properties

Changes update the canvas immediately.

---

# Example Configuration

Element: Cliente

Position
X: 120
Y: 80

Size
Width: 200
Height: Auto

Typography
Font: Helvetica
Size: 12
Weight: Bold

Color
#000000

Alignment
Left

---

# Benefits

The Element Inspector allows:

precise layout control
fine typography adjustments
conditional field visibility
data binding configuration
visual styling

This level ensures operators can perfect the final document layout.

---

# Summary

The Element Inspector manages **individual document elements** such as:

Text
Fields
Labels
Icons
Inline images

It provides control over:

position
size
typography
color
spacing
alignment
visibility rules
data bindings

This is the **most detailed editing layer in the Template Editor**.
