
# Template Editor — Inspector Level 3
# Component Inspector Specification

## Overview

The **Component Inspector** is responsible for configuring **complex layout components**
inside document sections.

While the Element Inspector manages simple items (text, labels, fields), the
Component Inspector manages **structured components** that contain internal logic.

Typical components include:

- Tables
- Charts
- Containers / Groups
- Images
- Repeating blocks

These components often interact with:

- data bindings
- pagination rules
- layout flow behavior

---

# Position in Inspector Hierarchy

Inspector hierarchy:

1. Page Inspector
2. Section Inspector
3. Component Inspector
4. Element Inspector

The Component Inspector manages **mid-level layout objects** that group or render
multiple elements.

---

# Where the Component Inspector is Accessed

The Component Inspector is activated when the user selects a **component node**.

Two main access methods:

## Method 1 — Structure Tree

Example:

Document
 ├ Header
 ├ Flow
 │   └ Table movimentos
 └ Footer

Selecting **Table movimentos** activates the Component Inspector.

## Method 2 — Canvas

Clicking a component directly in the canvas also activates the inspector.

Example:

Click on table → Table Inspector

---

# UI Placement

The Component Inspector appears in the **Inspector Panel** on the right side of the editor.

Editor layout:

Toolbar
Structure Tree | Canvas | Inspector Panel

Selecting a component changes the inspector view to the appropriate component settings.

---

# Supported Component Types

The system supports multiple component types.

Common components:

Table  
Chart  
Container  
Image

Each component type has specialized settings.

---

# Table Component

Tables are one of the most important components because they often render
data collections.

Example structure:

Table movimentos
 ├ descricao
 ├ valor
 └ data

---

## Table Inspector Settings

Data Source
movimentos

Columns

descricao width 60%
valor width 25%
data width 15%

Row Settings

Row Height
Padding

Pagination

Allow Page Break
Repeat Header

Sorting
Optional

---

## Table Behavior

Tables automatically expand depending on the data size.

Example:

movimentos = 3 rows → table fits on page

movimentos = 200 rows → table flows across pages

The layout engine handles pagination automatically.

---

# Chart Component

Charts visualize structured data.

Supported chart types:

Bar chart  
Line chart  
Pie chart  

Charts are rendered using **Chart.js** in the final HTML template.

---

## Chart Inspector Settings

Chart Type
Bar / Line / Pie

Data Source
salesData

Category Field
month

Value Field
revenue

Color Scheme

Primary
Secondary

Size

Width
Height

---

# Container Component

Containers group multiple elements.

Example:

Container CustomerInfo
 ├ Cliente
 ├ CPF
 └ Address

---

## Container Inspector Settings

Layout

Vertical
Horizontal

Spacing

Item spacing
Padding

Alignment

Left
Center
Right

Containers help organize related elements.

---

# Image Component

Images include logos or decorative assets.

Example:

Logo

---

## Image Inspector Settings

Source

Upload Image
URL

Sizing

Width
Height

Scaling

Fit
Contain
Stretch

Alignment

Left
Center
Right

---

# Component Pagination Behavior

Some components can span multiple pages.

Example:

Tables

Component settings may include:

Allow Page Break

If disabled, the entire component must stay together.

---

# Component Anchors

Components may have layout anchors.

Examples:

Flow Anchor
Top Anchor
Bottom Anchor

These anchors define how the component interacts with page layout.

---

# Data Binding

Components often bind to data structures.

Example:

Table movimentos → {{movimentos}}

Chart vendas → {{vendasMensais}}

Bindings define which data drives the component.

---

# Interaction Behavior

Selecting a component:

1. highlights the component in the canvas
2. opens the Component Inspector
3. loads component-specific settings

---

# Example Configuration

Table Component

Data Source: movimentos

Columns
descricao 60%
valor 25%
data 15%

Row Height: 28px

Allow Page Break: YES

Repeat Header: YES

---

# Benefits

The Component Inspector enables:

control of structured elements
data-driven layouts
complex rendering logic
automatic pagination handling

Without this layer, managing tables and charts would be difficult.

---

# Summary

The Component Inspector manages **structured layout components** such as:

Tables
Charts
Containers
Images

It provides configuration for:

data bindings
layout behavior
pagination
component sizing
visual styling

This inspector is essential for building dynamic document templates.
