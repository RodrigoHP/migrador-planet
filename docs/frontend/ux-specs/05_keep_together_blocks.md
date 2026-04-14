# Keep Together Blocks

Certain content blocks must not split across pages.

Examples:

- Address blocks
- Financial summaries
- Signatures
- Charts

## Behavior

If block height > remaining page space:

Move block to next page.

## Example

Page 1
Content
Content

Page 2
Summary block

## Template Flag

{
  "keepTogether": true
}