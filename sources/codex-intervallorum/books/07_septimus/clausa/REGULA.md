# Regula

The rule by which the seven fields of the Nota Clausa were grown, printed whole. It follows the rule of the notae in Book V (sense, turn, move, deposit, diffuse and evaporate, one agent to a cell) after Jones [V/S9], restated in whole numbers so that it gives the same result in any language on any machine. Nothing in it is secret. The only secret is the key, and the Tabula says where the key is.

Every division below is a division of whole numbers rounding down. Every quantity divided is positive by construction. Every "mod 32" gives a heading from 0 to 31.

## I. The ground

1. The ground is a square of 260 × 260 cells, *x* and *y* each running from 0 to 259. Cell (*x*, *y*) belongs to the arena when (2x + 1 − 260)² + (2y + 1 − 260)² ≤ 236². The arena holds 43,748 cells.
2. A position is a pair of whole numbers in 256ths of a cell. The cell of position (*p*, *q*) is (*p* ÷ 256, *q* ÷ 256).
3. There are 32 headings, numbered 0 to 31. Heading *h* moves a position by (C[*h*], S[*h*]), where C is this table and S[*h*] = C[(*h* − 8) mod 32]:

   | *h* | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | C | 256 | 251 | 237 | 213 | 181 | 142 | 98 | 50 | 0 | −50 | −98 | −142 | −181 | −213 | −237 | −251 |

   | *h* | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 | 31 |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | C | −256 | −251 | −237 | −213 | −181 | −142 | −98 | −50 | 0 | 50 | 98 | 142 | 181 | 213 | 237 | 251 |

4. Constants: sensor offset 9; sensor angle 4 headings; rotation 4 headings; deposit 1280; the field keeps 236 parts in 256 at each step; 1266 steps; 7920 agents.
5. The field is a whole number for every cell of the ground, all 0 at the start.

## II. The lot

6. Chance is SplitMix64 on a state *s* of 64 bits, all arithmetic modulo 2⁶⁴:

   ```
   next():  s ← s + 0x9E3779B97F4A7C15
            z ← s
            z ← (z XOR (z >> 30)) × 0xBF58476D1CE4E5B9
            z ← (z XOR (z >> 27)) × 0x94D049BB133111EB
            return z XOR (z >> 31)
   below(n): return next() mod n
   ```

7. The key is a phrase of capital letters and single spaces. For field *k* (1 to 7), the starting state *s* is the first eight bytes, read big-endian, of the SHA-256 digest of the ASCII text made of the key, the character `/`, and *k* written in decimal. For a key `ALPHA BETA` and field 3, the digested text is `ALPHA BETA/3`.

## III. The planting

8. List the arena's cells in order of *y*, then of *x*, both ascending. Shuffle the list: for *i* from its last index down to 1, take *j* = below(*i* + 1) and exchange the entries at *i* and *j*.
9. Agent *a*, for *a* from 0 to 7919, is planted at the centre of the cell at place *a* of the shuffled list, counting places from 0: if that cell is (*x*, *y*), its position is (256x + 128, 256y + 128). Each agent holds the cell it is planted on. Planting deposits nothing.
10. Then, for *a* from 0 to 7919 in order, the heading of agent *a* is below(32).

## IV. One step

11. Make the list 0, 1, …, 7919 and shuffle it as in clause 8. The agents act one at a time in that order. The field is read and written in place: an agent senses what earlier agents in the same step have deposited.
12. **Sense.** For an agent at (*p*, *q*) with heading *h*, take three headings: left = (*h* + 4) mod 32, ahead = *h*, right = (*h* − 4) mod 32. For each, the sensed cell is ((*p* + 9·C[*e*]) ÷ 256, (*q* + 9·S[*e*]) ÷ 256), where *e* is that heading. Its value is the field at that cell if the cell is in the arena, and −1 otherwise. Call the three values *L*, *A* and *R*. Only sensing gives −1; the field itself is 0 outside the arena. Left and right are names for the formulas: *y* runs down the sheet, so a turn to the left is clockwise as drawn.
13. **Turn.** If *A* > *L* and *A* > *R*, keep *h*. Otherwise, if *A* < *L* and *A* < *R*, draw below(2): on 0 the new heading is (*h* + 4) mod 32, on 1 it is (*h* − 4) mod 32. Otherwise, if *L* > *R*, the new heading is (*h* + 4) mod 32. Otherwise, if *R* > *L*, it is (*h* − 4) mod 32. Otherwise keep *h*. Call the result *t*.
14. **Move.** The proposed position is (*p* + C[*t*], *q* + S[*t*]). Its cell may be taken if it is in the arena and either no agent holds it or the moving agent itself holds it.
    - If it may be taken, the agent's position becomes exactly the proposed position, not the centre of its cell. If its cell changed, it holds the new cell and releases the old one at once, so a later agent in the same step may take it. It adds 1280 to the field at its cell, also when the move kept it in the same cell. Its heading becomes *t*.
    - If not, the agent stays where it is, deposits nothing, and its heading becomes below(32).
15. **Field.** When every agent has acted, replace the field at once: for each cell, add the nine values of the 3 × 3 block centred on it, counting places off the ground as 0; divide by 9; multiply by 236; divide by 256. Cells outside the arena become 0.
16. Repeat clauses 11 to 15 for 1266 steps. The cell each agent holds at the end is its last cell.

No two agents ever hold one cell, so the last cells of the 7920 agents are 7920 different cells. They are the marks on the plate.

## V. The reading

17. On each plate every mark stands on a cell, red or black. Red is 1, black is 0. The marks are the two-point strokes of the plot sheet's Art Paths layer; rings, contours and the reserved blank are drawn with more points, and lettering is in the Text Outlines layer. A mark's cell is the cell its stroke is centred on; the direction of the stroke is the agent's last heading and is not needed for reading. On the A4 plot sheet, measured in millimetres from its top left corner, cell (*x*, *y*) is centred at (14.35 + 0.7x, 61.35 + 0.7y), so the ground's centre is the sheet's point (105, 152). The red ring is the arena's edge. A reading edition may scale the sheet, never distort it.
18. Regrow the field from its key. For agents 0 to 7919 in order, read the colour of the mark on that agent's last cell. This gives 7920 figures.
19. Take the figures six at a time, the first of each six the most significant. Each six is a number from 0 to 63. Read the number as a sign in this table, where ¶ is the end of a line:

    |  | +0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 |
    |---|---|---|---|---|---|---|---|---|
    | 0 | space | A | B | C | D | E | F | G |
    | 8 | H | I | J | K | L | M | N | O |
    | 16 | P | Q | R | S | T | U | V | W |
    | 24 | X | Y | Z | 0 | 1 | 2 | 3 | 4 |
    | 32 | 5 | 6 | 7 | 8 | 9 | . | , | ; |
    | 40 | : | ' | - | / | [ | ] | ¶ | ( |
    | 48 | ) | ? | ! | " | & | + | = | * |
    | 56 | # | % | < | > | @ | _ | \| | ~ |

20. Each field gives 1320 signs. A field's text ends with spaces where its article is shorter than the field.

## VI. The proof of a reading

21. Write each reading as 1320 ASCII characters, with ¶ as the line-feed character (10). The SHA-256 digest of each reading, and of the seven readings joined in order with nothing between them, are printed in the Tabula. A reading that matches its digest is the reading. No one else's word is needed for it.

