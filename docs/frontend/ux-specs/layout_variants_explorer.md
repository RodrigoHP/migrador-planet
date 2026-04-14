
# Layout Variants Explorer — Detailed Specification

## Purpose

Layout Variants Explorer is a UI module used to analyze **multiple PDF examples of the same document type**
and detect **layout variations automatically**.

This component helps the system identify:

- different page structures
- optional sections
- conditional blocks
- layout shifts caused by different data

Instead of editing each PDF separately, the user edits **one unified template that supports variants**.

---

# Problem It Solves

When working with document templates it is common to have:

- multiple PDFs of the same document type
- slight layout differences between them
- optional fields that appear only sometimes
- blocks that are conditionally rendered

Example:

PDF 1

Cliente  
CPF  
Tabela  
Subtotal  

PDF 2

Cliente  
CPF  
Telefone  
Tabela  
Subtotal  

Here the field **Telefone** is optional.

Without variant detection the user would need to manually compare documents.

Layout Variants Explorer automates this process.

---

# Where It Appears In The UI

The Layout Variants Explorer appears in the **left panel of the editor**.

Example layout:

+-------------------------------------------------------------+
| Layout Variants Explorer                                    |
|-------------------------------------------------------------|
| Base Layout                                                 |
|   ├ Variant A (PDF 1)                                       |
|   ├ Variant B (PDF 2)                                       |
|   └ Variant C (PDF 3)                                       |
|                                                             |
| Differences Detected                                        |
|   - Optional Field: Telefone                                |
|   - Optional Section: Observações                           |
+-------------------------------------------------------------+

The system groups PDFs by **structural similarity**.

---

# Variant Detection Pipeline

When multiple PDFs are uploaded the system performs:

1. Layout analysis
2. Structural fingerprinting
3. Layout clustering
4. Variant comparison

Result:

Different layouts are grouped into **variants**.

Example:

Uploaded PDFs:

PDF1
PDF2
PDF3
PDF4

Detected layouts:

Layout Cluster A
PDF1
PDF2
PDF3

Layout Cluster B
PDF4

The editor will show:

Base Layout  
Variant A  
Variant B

---

# Visual Comparison Mode

Users can visually compare layout variants.

Example UI:

+-----------------------------------------------------------+
| Variant Comparison                                        |
|-----------------------------------------------------------|
| Variant A | Variant B                                     |
|-----------------------------------------------------------|
| Cliente   | Cliente                                       |
| CPF       | CPF                                           |
|           | Telefone                                      |
| Tabela    | Tabela                                        |
| Subtotal  | Subtotal                                      |
+-----------------------------------------------------------+

Differences are highlighted.

---

# Highlighted Differences

The system categorizes differences as:

Optional Field
Optional Section
Position Shift
Style Difference

Example:

Telefone → Optional Field

---

# Optional Elements

When a field exists in some PDFs but not others the system marks it as optional.

Example:

Telefone appears in 3 of 5 documents.

The editor displays:

Telefone (Optional)

---

# Conditional Blocks

Some sections appear only when certain data exists.

Example:

Observações

The system generates a conditional rule.

Example template logic:

IF observacoes EXISTS
SHOW Observações section

---

# User Interaction

The user can:

Approve optional fields
Merge layout variants
Ignore differences
Convert elements into conditional blocks

Example actions:

Mark as Optional  
Create Condition  
Merge Layouts

---

# Variant Merge Strategy

Variants can be merged into a unified template.

Example:

Variant A

Cliente
CPF
Tabela

Variant B

Cliente
CPF
Telefone
Tabela

Merged template:

Cliente
CPF
IF telefone EXISTS
Telefone
Tabela

---

# Data Structure

Internally the system stores variant information.

Example:

{
 "variants": [
   {
     "name": "Variant A",
     "documents": ["pdf1","pdf2","pdf3"]
   },
   {
     "name": "Variant B",
     "documents": ["pdf4"]
   }
 ]
}

---

# Confidence Scoring

Variant detection also produces confidence scores.

Example:

Optional Field Detection → 87%
Layout Match → 92%

Low confidence items are highlighted for review.

---

# Integration With Editor

Layout Variants Explorer connects with:

Field Navigator
Template Editor
Condition Builder
Confidence Map

Selecting a variant automatically updates the preview page.

---

# Workflow Example

1 Upload multiple PDFs

2 System detects layout clusters

3 Layout Variants Explorer displays clusters

4 User reviews differences

5 Optional fields become conditions

6 Unified template is generated

---

# Benefits

Reduces manual comparison
Automatically detects optional elements
Simplifies template creation
Supports multiple layout variations
Improves template robustness

---

# Summary

Layout Variants Explorer enables the system to:

detect structural differences between documents
convert differences into template conditions
create a single reusable template capable of handling multiple layout variants
