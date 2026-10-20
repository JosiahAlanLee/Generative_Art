# Process-art R&D — 20 October 2026

Prepared with ChatGPT/Codex for Josiah Alan-Lee. The initial review covered the
current technique catalog, native SVG importer, plotter Hand, geometry core and
raster adapters. Four new studies fill gaps around geological evolution,
chemical morphogenesis and declared time-series relationships. All code is an
independent implementation; no third-party source code or figures were copied.

## Dendritic ledger: a field that changes before it is engraved

The model begins with multiscale terrain, conditions closed depressions with a
priority queue, and directs each interior cell to its steepest lower D8 neighbor.
Every cell contributes one runoff unit; accumulation is summed in descending
elevation order. Incision per step is proportional to `K * sqrt(A) * slope`,
capped at 30% of the downstream elevation drop. A linear Laplacian term diffuses
the hillslopes. The black contours and red channels come from the resulting
terrain and receiver graph.

This is a dimensionless, stream-power-inspired art model. Howard's model is
substantially broader, including slumping and transport-limited processes that
are absent here. Our fixed edges, routing epsilon, grid anisotropy and simplified
sink treatment affect the drawing. There is no sediment budget, deposition,
real watershed calibration or estimate of elapsed geological time. Channel-path
smoothing is an explicitly recorded cartographic rendering step.

**Sources:** [Howard (1994), A detachment-limited model of drainage basin
evolution](https://doi.org/10.1029/94WR00757);
[Barnes, Lehman and Mulla (2014), Priority-Flood](https://doi.org/10.1016/j.cageo.2013.04.024).
The queue implementation here is deliberately small and does not implement
every optimization in Priority-Flood.

**Useful extension:** route one basin through a mechanical apparatus, then grow
the book's image-fed cultures against the accumulation field. Keep the routed
basin and agent trails as separately identified layers.

## Fault archive: deformation, not another layer of random noise

An implicit age coordinate begins with ordered beds. Smooth sinusoidal
deformation bends that coordinate; two curved fault boundaries add opposite
offsets. Contouring age draws the beds. Narrow masked seams prevent false
connections across fault jumps; red selected beds make offsets readable. A
weathered specimen boundary and top truncation expose a section.

This kinematic construction is original to this study. It is not an elastic,
plastic, tectonic, sedimentation or time-evolution solver. Noise provides a
small material irregularity. The visible changes are primarily the declared
coordinate deformation and fault offsets. Sparse hatches follow the age-field
gradient and are a drawing treatment.

**Useful extension:** make several apparatus components from one shared age
field so their bedding registers across the page, then offset only the parts
that have undergone a declared fault operation. This would turn geological
continuity into a compositional constraint.

## Vascular palimpsest: chemistry actually drives the second process

We integrate the Gray–Scott equations with explicit Euler steps:

```text
u_next = u + Du*laplace(u) - u*v*v + F*(1-u)
v_next = v + Dv*laplace(v) + u*v*v - (F+k)*v
```

The presets use `Du=.16`, `Dv=.08`, `dt=1`, cell spacing 1 and reflecting edges.
Finite-amplitude patches seed the field. V concentration changes the probability
of accepting candidate attraction points: `p=.10+.82*clip(V/.35,0,1)`. Space
colonization then grows tree edges toward nearby accepted points and retires
points within its kill radius. Black chemical contours and red tree edges are
different products of that coupling. Subtree size controls drawing width.

This is a one-way hybrid: veins do not consume or alter the chemical field.
Geometric clipping creates the specimen and empty aperture after growth, so
those edges are drawing boundaries rather than chemical boundary conditions.
It is not the existing Physarum model, a physiological vascular model, or a
claim to have demonstrated a Turing instability. Tree ancestry has no cycles;
crossings in a 2D drawing are not new graph junctions.

**Sources:** [Pearson (1993), Complex Patterns in a Simple
System](https://arxiv.org/abs/patt-sol/9304003);
[MIT Gray–Scott model notes](https://groups.csail.mit.edu/mac/projects/amorphous/GrayScott/);
[Runions et al. (2005), Modeling and visualization of leaf venation
patterns](https://algorithmicbotany.org/papers/venation.sig2005.html);
[Runions, Lane and Prusinkiewicz (2007), Modeling Trees with a Space Colonization
Algorithm](https://algorithmicbotany.org/papers/colonization.egwnp2007.html).
Our implementation uses a 2D nearest-node simplification rather than reproducing
the full 2005/2007 modeling systems.

**Useful extension:** let vein occupancy lower chemical feed locally and compare
the resulting morphology against this saved one-way baseline. That would be a
new bidirectional experiment, not a property of the current images.

## Return engine and recurrence loom: a recoverable data key

For row `i`, the state vector is `[x[i], x[i+2], x[i+4]]`. Each coordinate is
standardized using its finite-window population mean and standard deviation.
Two states recur when their Euclidean distance is at most epsilon, with original
row separations of five or less excluded. Missing windows are omitted rather
than filled. Every eligible pair is retained.

The circular composition puts time rows around an ellipse and draws one curve
for each undirected recurrence. Curvature is decorative. The loom draws both
symmetric entries of the same type of matrix, black below the diagonal and red
above it. The red outer/top trace is the min-max scaled input series. Variant 1
also changes the synthetic input after row 110 and uses a different epsilon;
their image densities are not evidence for a difference between real systems.

The supplied examples are explicitly synthetic. Their exact CSVs, settings,
matrix and row indices are included. A real CSV can be supplied through the
same interface with its hash retained. Angular or grid spacing records row
order, not elapsed time; meaningful irregular-time analysis needs a separate,
declared preprocessing decision. No claim of causality, chaos or institutional
failure follows from recurrence alone.

**Source:** [Marwan, Romano, Thiel and Kurths (2007), Recurrence Plots for the
Analysis of Complex Systems](https://doi.org/10.1016/j.physrep.2006.11.001),
with [author-deposited text](https://arxiv.org/abs/2501.13933). The 2025 arXiv
submission is the archived version of the 2007 review, not a new 2025 result.

**Useful extension:** feed the exported Gray–Scott mean-V telemetry into the
recurrence renderer. This makes a data ornament from a documented model run
and allows the figure and its temporal behavior to share an auditable origin.

## Selection and practical limits

Candidates were rendered before selection and reviewed as a contact sheet and
at page scale. The selection favors readable negative space, coherent contour
rhythm, legible differences between red and black structures, and images that
contribute different compositions. It does not rank scientific fidelity.

Geometry is exported as absolute millimetre M/L paths with explicit stroke
attributes because the existing book SVG importer reads those reliably. PNGs
are previews; the SVG/NPZ pair preserves the drawing and process state for later
placement or combination. Physical plotting and a full Codex binding rebuild
are outside this study's verification. The R&D does not modify book text,
cipher carriers, art slots or the preserved upstream snapshot.
