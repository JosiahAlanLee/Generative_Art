# Validation of this collection

Checked on 20 October 2026 with Python 3.12. This records the import/organization change, not a new validation of the three pre-existing scene studies or the whole illustrated edition.

| Check | Observed result |
| --- | --- |
| Imported bytes and complete Python coverage | 241 files match upstream SHA-256 and Git blob identities; all 117 tracked Python modules retained and parsed |
| Catalog and authored navigation | 30 unique technique entries; 8 family guides; all checked local links resolve |
| Six-panel sampler | SVG, PNG and manifest generated; visual inspection passed; repeat SVG and manifest identical |
| Production Notoria I | Built 2,048 strokes, including 1,118 art and 930 text strokes; 12.9 m measured pen-down length |
| Notoria plate validation | All five exported SVG passes passed; caption and hidden carrier round trips passed; margins and reserved blank passed |
| Notoria field regeneration | Code hash, recomputed manifest identifier and regenerated field matched; frame carries the correct identifier |
| Existing figure-growth suite | 5 tests passed: deterministic field, monotone masks, protected pixels, selected fringe and carrier/decorative boundaries |
| Existing vellum suite | 11 tests passed: protection, repeatability, light profile, exact source preservation and double-application checks |
| Existing scribal suite | 8 tests passed: clear paper, text/cipher protection, page identity and preservation checks |
| Semiphoras command | Generated all 72 names and passed its round trip |

Native Notoria outputs used for these checks are generated under `examples/out/` and are not committed. The committed preview is a small demonstration, not a reproduction of the book plates. Physical plotting was not tested. The existing Blender, Photophobic and statue build records remain as supplied; those studies were not rerun.
