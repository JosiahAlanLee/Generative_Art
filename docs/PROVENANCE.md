# Source provenance and updates

The book source is the public repository [`JosiahAlanLee/Codex-Intervallorum`](https://github.com/JosiahAlanLee/Codex-Intervallorum), main commit `b789e03f30034bc8403f8a40aaf83842885aaad5`, inspected on 20 October 2026. No private development repository was copied. The three pre-existing studies remain at their existing paths and are not part of the imported book snapshot.

The snapshot preserves all **117 tracked Python modules**, including visual techniques, integration/build code, validators and small model dependencies. It also retains selected technical inputs, fonts/notices and source SVGs. The [full module index](SOURCE_INDEX.md) separates those roles. There are 241 included files and 569 upstream file paths accounted for in [source-manifest.json](../catalog/source-manifest.json).

Book manuscripts and upstream provenance records are omitted, along with large raster illustrations, edition PDFs, caches and repository administration. The imported material is limited to public technique code, font notices, source SVGs and selected technical inputs. Each omission has an explicit manifest reason. Raster/compositing and edition builders are retained for inspection and adaptation; they require the corresponding omitted art to rebuild the full illustrated book. The few retained technical Markdown files are byte-identical and can still link to an omitted edition or image. Book prose and upstream provenance metadata remain in the source repository.

No source module was rewritten, renamed or deduplicated. Copies of `core.py`, `marks.py`, `tx.py`, fonts and proof helpers remain where the book put them because the original scripts rely on those paths and may represent different source editions. Their shared or differing content is visible through Git blob IDs and SHA-256 hashes. Use the family guides to find a preferred entry point rather than deleting dependencies.

Nota Clausa is the explicit exception to regeneration: the public repository contains its printed rule, tabula, sealed SVGs, layout builder and validator, but no key, plaintext or enciphering script. It is cataloged as a sealed artifact. The current source does not contain aebrer’s entropy-locking implementation, reaction–diffusion or the other proposed research algorithms; these are not represented as imported code.

## Updating deliberately

Use a clean checkout of a reviewed public book commit, and create a branch in this repository. The import tool reads only the supplied local checkout; it does not fetch or choose a new revision.

```sh
python tools/snapshot_book.py /path/to/Codex-Intervallorum --commit FULL_COMMIT_SHA
python tools/verify_collection.py
```

The importer verifies each selected checkout file against its Git blob before copying. It refreshes the manifest and source index. It does not delete files removed upstream, rewrite the authored family guides, discover new technique groupings or change the existing studies. Review the diff, remove any retired snapshot paths explicitly, revise the catalog and snapshot counts, then rerun the examples and relevant validators. This preserves a review point when the book’s APIs or build inputs change.
