
# Document Template Engine
## Template Saving Strategy (MVP)

---

# 1. Objective

Define the saving strategy for templates in the **PlanetPress → HTML Template Engine**.

The goal of saving is to allow the editor to be **reopened exactly in the same structural state**, without executing again:

- pipeline analysis
- OCR
- Vision
- layout detection
- asset extraction

Conceptually:

Save Template → Export Editor State → Open Template → Restore Editor State

The saved template acts as a **complete editor state package**.

---

# 2. MVP Principles

To simplify the MVP:

## No Database
Templates are stored **locally as a file**.

## Template is a Package
Templates are exported as:

template.zip

## Opening a Template Does Not Run the Pipeline
Opening a template must **NOT execute**:

- Vision
- OCR
- Layout detection
- Asset extraction

Everything necessary must already be saved.

## Editor State Restoration
Opening the template restores:

- Canvas
- Structure tree
- Bindings
- Rules
- Assets
- Example PDFs

---

# 3. Template Package Structure

template.zip

├ template.json  
├ schema.json  

├ examples/  
│ ├ example1.pdf  
│ ├ example2.pdf  

├ assets/  
│ ├ logo.png  
│ ├ header_background.png  

├ fonts/ (optional)  
│ └ custom_font.woff  

└ layout/  
  └ skeleton.json

Each file has a specific purpose.

---

# 4. template.json

This file contains the **complete template structure**.

It represents the **editor structural state**.

Includes:

- page configuration
- sections
- components
- elements
- bindings
- rules
- anchors
- styles
- layout positions

Example:

{
  "templateId": "bank_statement",

  "page": {
    "size": "A4",
    "margins": {
      "top": 20,
      "bottom": 20,
      "left": 15,
      "right": 15
    }
  },

  "sections": [
    {
      "id": "header",
      "elements": [
        {
          "type": "text",
          "binding": "cliente.nome",
          "position": { "x": 100, "y": 50 }
        }
      ]
    }
  ],

  "components": [
    {
      "type": "table",
      "dataSource": "movimentos"
    }
  ]
}

This file reconstructs:

- Canvas
- Structure Tree
- Element hierarchy

---

# 5. schema.json

This file contains the **XSD converted to JSON**.

Example:

{
  "cliente": {
    "nome": "string",
    "cpf": "string"
  },

  "movimentos": [
    {
      "descricao": "string",
      "valor": "string"
    }
  ]
}

Used for:

- data binding
- rule configuration
- validation
- automatic field mapping

---

# 6. examples/

Example PDFs used in the editor for visual reference.

examples/
 ├ example1.pdf
 ├ example2.pdf

Used for:

- Multi PDF Viewer
- layout comparison
- layout variants
- visual guidance

These PDFs are **not reprocessed** when reopening the template.

---

# 7. assets/

Images extracted from the document layout.

assets/
 ├ logo.png
 ├ header_background.png
 └ signature.png

Used directly by the editor to reconstruct the layout.

---

# 8. fonts/

Optional directory.

Exists only if the operator imported a custom font.

fonts/
 ├ custom_font.woff

Otherwise the editor can use fallback fonts.

---

# 9. layout/skeleton.json

Stores the **detected layout structure**.

Example:

Document
 ├ Header
 │ ├ Logo
 │ └ Client Name
 │
 ├ Flow
 │ └ Transactions Table
 │
 └ Footer
   └ Page Number

Used to:

- reconstruct layout structure quickly
- preserve anchors
- avoid running layout detection again

---

# 10. Data NOT Saved

These intermediate pipeline outputs are **not persisted**:

- raw OCR output
- raw Vision output
- bounding box detection results
- confidence scores
- token analysis
- paragraph detection

They are only needed during initial template generation.

---

# 11. Save Flow

Save Template
↓
Serialize editor state
↓
Export template.json
↓
Export schema.json
↓
Copy example PDFs
↓
Copy detected assets
↓
Copy custom fonts (if any)
↓
Export skeleton layout
↓
Create template.zip
↓
Download

---

# 12. Open Flow

Open Template
↓
Select template.zip
↓
Unzip package
↓
Load template.json
↓
Load schema.json
↓
Load assets
↓
Load fonts
↓
Load example PDFs
↓
Load skeleton layout
↓
Rebuild editor state

Result:

Editor opens instantly without running the pipeline again.

---

# 13. UI State Not Saved

To simplify the MVP the template does NOT store:

- viewport position
- zoom level
- scroll position
- selected element
- UI layout state

The editor opens in neutral state.

---

# 14. Benefits

## Instant Template Loading
No pipeline re-execution required.

## Portable Template
The template.zip file can be:

- shared
- versioned
- archived

## Infrastructure Independent
No database or cloud required.

## Future Evolution
This package format can later be imported into a Template Registry.

---

# 15. Conclusion

The template works as a **complete editor state package**.

template.zip contains:

- template structure
- schema
- example documents
- assets
- optional fonts
- layout skeleton

This ensures the editor can be fully reconstructed without re-running the document analysis pipeline.
