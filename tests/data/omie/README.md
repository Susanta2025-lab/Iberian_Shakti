# OMIE Stage 4 fixtures

`manifest.json` inventories every data fixture and its exact-byte SHA-256.
Native revision filenames are original complete downloads retained in `/tmp`
from the accepted 2026-10-26 assessment, copied without decoding or rewriting.
The three hashes printed in that assessment were checked before copying.
Other original samples match the accepted filenames, lengths, and row profiles;
the manifest records their hashes. No download occurred during Stage 4.

`synthetic_*` files are complete generated days, including the unverified legacy
autumn profile and first modern delivery day. `revised_*` is a controlled valid
mutation, not an observed revision. The malformed `.omie` files are intentional
mutations of the ordinary modern sample (HTML is a replacement body). They are
not valid shortened days. Listing HTML is synthetic, modelling allowlisted
same-origin download anchors and a pager; it is not captured provider HTML.

Tests load local bytes only. To change fixtures intentionally, update the
manifest hash and purpose, preserve original bytes/attribution, and distinguish
original, synthetic, and mutated evidence. A parser change must not relabel
synthetic source facts as verified live facts. No bulk historical dataset belongs
here. Do not normalize CRLF in original files.
