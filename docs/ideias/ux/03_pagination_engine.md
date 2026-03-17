# Pagination Engine Specification

## Goal
The generated HTML must already contain correct pagination.

The PDF engine does not determine page breaks.

## Page Structure

<div class="page">
  <header></header>
  <main></main>
  <footer></footer>
</div>

## Pagination Strategy

Render → Measure → Paginate

Steps:

1. Render HTML content
2. Measure DOM element heights
3. Detect overflow beyond page height
4. Move elements to next page
5. Generate new page container

## Page Size

Example A4:

width: 210mm
height: 297mm

## Output

<div class="page">Page 1</div>
<div class="page">Page 2</div>