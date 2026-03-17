
# Template Editor — Page Configuration & Element Configuration Specification

This document describes in detail the **Page Configuration** and **Element Configuration** parts of the Template Editor UI.

These controls allow users to precisely define:

- page size
- margins
- header/footer regions
- element positioning
- spacing
- typography
- layout constraints

This specification focuses only on **page-level and element-level configuration**.

---

# 1. Page Configuration (Page Setup)

The Page Setup defines the **physical layout of the document page**.

Users access this configuration via:

Page Settings button in the editor toolbar.

Example toolbar:

[Page Settings] [Snap ON] [Preview] [Save Template]

---

# 2. Page Settings Panel

Opening Page Settings displays the following configuration panel.

Page Size  
• A4  
• Letter  
• Custom

Width  
Height

Orientation  
• Portrait  
• Landscape

Margins  
Top  
Bottom  
Left  
Right

Header Height  
Defines the reserved area at the top of each page.

Footer Height  
Defines the reserved area at the bottom of each page.

Content Area Height  
Automatically calculated.

---

# 3. Page Layout Zones

After configuration the editor displays visual regions.

HEADER REGION

Used for elements that repeat on every page.

Examples:

logo  
document title  
customer name

CONTENT FLOW REGION

Dynamic area where content grows and pagination occurs.

Examples:

tables  
charts  
paragraphs

FOOTER REGION

Area repeated on every page.

Examples:

page number  
totals  
signature

---

# 4. Page Guides

The editor shows page guides to help alignment.

Guides include:

Margin boundaries  
Header boundary  
Footer boundary  
Content area

These guides are displayed as visual lines in the editor canvas.

---

# 5. Element Configuration

When a user selects an element in the editor canvas, the **Element Inspector Panel** appears.

The inspector allows modification of layout and styling properties.

---

# 6. Element Position

Elements are positioned relative to their container region.

Position controls:

X coordinate  
Y coordinate

Example:

X: 120 px  
Y: 80 px

This allows precise placement on the canvas.

---

# 7. Element Size

Size controls define element dimensions.

Width  
Height

Options:

Fixed width  
Auto height (for text)

Example:

Width: 300 px  
Height: auto

---

# 8. Spacing Controls

Spacing determines the internal and external spacing of the element.

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

Example:

Padding Top: 5 px  
Margin Bottom: 10 px

---

# 9. Typography Configuration

Text elements include typography settings.

Font Family  
Font Size  
Font Weight  
Text Color  
Alignment  
Line Height

Example:

Font Family: Helvetica  
Font Size: 12 px  
Font Weight: Bold  
Alignment: Left

---

# 10. Text Behavior

Additional text controls include:

Allow Text Wrap  
Overflow Handling

Options:

Wrap text  
Clip text  
Auto expand container

---

# 11. Element Alignment Tools

The editor includes alignment shortcuts.

Align Left  
Align Center  
Align Right

Distribute Horizontal  
Distribute Vertical

These tools assist in maintaining consistent layouts.

---

# 12. Snap Behavior

Elements can snap to layout guides.

Snap targets:

Grid  
Margins  
Column guides  
Other elements

Snap lines appear during dragging operations.

---

# 13. Grid System

Optional grid overlay helps alignment.

Grid size example:

8 px

The grid improves layout consistency.

---

# 14. Element Layering

Elements can overlap. The editor manages stacking order.

Layer controls:

Bring Forward  
Send Backward  
Bring to Front  
Send to Back

---

# 15. Element Locking

Elements can be locked to prevent accidental movement.

Locked elements remain visible but cannot be dragged.

---

# 16. Responsive Width Constraints

Elements inside flow containers can use width constraints.

Options:

Fixed width  
Percentage width  
Auto width

Example:

Width: 70% of content area.

---

# 17. Element Anchoring

Elements can attach to layout regions.

Anchor options:

Top  
Flow  
Bottom

Anchors define how elements behave when pagination occurs.

---

# 18. Summary

Page configuration defines the structural layout of the document.

Element configuration defines the behavior and appearance of individual components.

Together they enable precise reconstruction of document layouts extracted from PDFs.
