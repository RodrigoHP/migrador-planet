
# Template Editor — Inspector Level 2
# Section Inspector Specification

## Overview

The **Section Inspector** controls the configuration of **document regions**.

In the document architecture, the page is divided into **three primary sections**:

- Header
- Flow (Content Flow)
- Footer

Each section has its own layout behavior and pagination rules.

The Section Inspector allows the operator to configure how these regions behave
during document rendering and pagination.

---

# Position in Inspector Hierarchy

Inspector hierarchy:

Page Inspector
Section Inspector
Component Inspector
Element Inspector

The Section Inspector is the **second level** in this hierarchy and controls
structural regions of the document.

---

# Sections in the Document Model

The document layout is structured as:

Document
 ├ Header
 ├ Flow
 └ Footer

Each of these nodes activates the Section Inspector.

---

# Where the Section Inspector is Accessed

The Section Inspector is activated when the user selects a **section node**.

## Method 1 — Structure Tree

User selects:

Header  
Flow  
Footer

Example:

Document
 ├ Header
 ├ Flow
 └ Footer

---

## Method 2 — Canvas

Clicking inside a section region also activates the inspector.

Example:

Click inside the header area → Header Inspector

---

# UI Placement

The Section Inspector appears in the **Inspector Panel** on the right side of the editor.

Editor layout:

Toolbar  
Structure Tree | Canvas | Inspector Panel

When a section is selected, the Inspector panel shows **Section Settings**.

---

# Section Inspector UI Layout

Example UI:

Section Settings
--------------------------------

Section Type
Header / Flow / Footer

Height
120px

Background
Color: #FFFFFF
Image: none

Padding
Top
Bottom
Left
Right

Repeat Behavior
Repeat on every page

Visibility
Always visible

---

# Section Types

The behavior of the inspector changes depending on which section is selected.

Section types:

Header  
Flow  
Footer

Each type has slightly different configuration options.

---

# Header Section

The Header section contains elements that appear at the **top of every page**.

Typical elements:

Logo  
Customer information  
Document title

Example structure:

Header
 ├ Logo
 ├ Cliente
 └ CPF

## Header Inspector Settings

Height  
Background Color / Image  
Padding  
Repeat on every page

Example:

Height: 120px  
Repeat on every page: YES

---

# Flow Section

The Flow section is the **main content area** of the document.

This region expands and may span multiple pages.

Typical content:

Tables  
Charts  
Paragraphs  
Lists

Example:

Flow
 └ Table movimentos

## Flow Inspector Settings

Flow Start Offset  
Padding  
Allow Page Breaks  
Vertical Spacing

Example:

Allow Page Breaks: YES

---

# Footer Section

The Footer section appears at the **bottom of each page**.

Typical elements:

Page number  
Signature area  
Legal text

Example:

Footer
 └ Page Number

## Footer Inspector Settings

Height  
Background  
Padding  
Repeat on every page

Example:

Height: 80px  
Repeat: YES

---

# Padding Configuration

Each section can define internal spacing.

Settings:

Padding Top  
Padding Bottom  
Padding Left  
Padding Right

Example:

Padding Top: 10px  
Padding Bottom: 10px

---

# Background Configuration

Sections may define background properties.

Options:

Background Color  
Background Image

Example:

Background Color: #F7F7F7

---

# Repeat Behavior

Header and Footer usually repeat on every page.

Setting:

Repeat on every page

Example:

Header → YES  
Footer → YES

Flow section does not repeat; it expands instead.

---

# Section Height

Header and Footer require a fixed height.

Example:

Header Height: 120px  
Footer Height: 80px

The Flow section automatically fills the remaining space.

---

# Content Area Relationship

Content area is calculated as:

Page Height
- Header Height
- Footer Height
- Margins

Remaining space becomes the **Flow region**.

Example:

Page Height: 842px  
Header: 120px  
Footer: 80px

Flow Height = 642px

---

# Interaction Behavior

Selecting a section highlights its region in the canvas.

Example:

User selects Header

Canvas highlights the header area.

Inspector shows Header settings.

---

# Section Locking

Sections can optionally be locked to prevent accidental editing.

Example:

Header locked → elements cannot be moved outside region.

---

# Example Configuration

Header Settings

Height: 120px  
Padding: 10px  
Repeat: YES

Flow Settings

Allow Page Breaks: YES  
Vertical spacing: 12px

Footer Settings

Height: 80px  
Repeat: YES

---

# Benefits

The Section Inspector allows:

Clear document structure  
Consistent header/footer behavior  
Reliable pagination control  
Logical separation of content regions

Without sections, document layouts would be difficult to manage.

---

# Summary

The Section Inspector defines **regional layout behavior** for:

Header  
Flow  
Footer

It controls:

Section height  
Background styling  
Padding  
Repeat behavior  
Pagination behavior

This inspector ensures the document layout remains organized and predictable.
