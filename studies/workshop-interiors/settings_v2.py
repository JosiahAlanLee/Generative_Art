"""Printed dimensions, inks, physical weights and declared tone zones."""
PX_PER_MM=20
INKS={'black':'#242820','red':'#a32b24'}
WEIGHTS_MM={'hatch':.10,'gap':.22,'silhouette':.25,'crease':.16,'backdrop':.12,'ornament':.12,'strand':.14,'cord':.14,'red_route':.32,'red_terminal':.40,'reserved_outline':.16}
SIZES={'maintained-workshop':(156,208),'empty-cabinet':(152,203),'extraction-of-the-hand':(95,119),'office-without-a-seal':(95,119)}
CAPTIONS={
 'maintained-workshop':'One hand checks the instrument. Another keeps the room warm.',
 'empty-cabinet':'The cabinet illustration is empty. No pictured body is assigned the role of hidden servant.',
 'extraction-of-the-hand':'The hand becomes a sequence; the sequence becomes a replacement; the replacement asks for the hand.',
 'office-without-a-seal':'There is a mounting point. There is a job description. There is no continuous path from the worker to the stop.',
}
# The targets describe hatch coverage, not a fictitious material albedo.
TONE={
 'maintained-workshop':{'service-bay':.75,'stove':.625,'underside':.55,'wheel':.50,'bookcases':.40,'rear-wall':.27,'deck':.18,'floor':.07,'structure':.35,'reserved':0},
 'empty-cabinet':{'interior-panels':.70,'top-underside':.60,'doors':.45,'exterior-panels':.45,'bench':.39,'bookcases':.275,'rear-wall':.16,'floor':.07,'mechanics':.42,'structure':.35,'reserved':0},
 'extraction-of-the-hand':{'under-bench':.75,'plinth':.55,'jig':.45,'apron':.40,'bookcases':.30,'bench-top':.16,'floor':.18,'structure':.35,'reserved':0},
 'office-without-a-seal':{'corners':.70,'reveal':.50,'shelf-undersides':.50,'instruments':.35,'lattice':.30,'back-wall':.20,'floor':.20,'structure':.35,'reserved':0},
}
HIERARCHY={
 'maintained-workshop':['service-bay','stove','bookcases','rear-wall-centre','deck'],
 'empty-cabinet':['interior-panels','doors','bench','bookcases','rear-wall'],
 'extraction-of-the-hand':['under-bench','plinth','jig','apron','bookcases','bench-top'],
 'office-without-a-seal':['corners','reveal','shelf-undersides','lattice','back-wall','halo'],
}
LIMITS=[
 'The procedural Blender model was built, saved and rendered.',
 'The final vector engraving uses evaluated Blender polygons with CPU ray visibility and Claude hatching functions.',
 'It is an interpretation of the book scene, not an exact reconstruction or a mechanical working model.',
 'No physical plot test has been performed; this is the print parameter set, not a scaled plot master.',
]

# Caller-side compensation for structural ink and very small face footprints.
ALLOCATION_MULTIPLIERS={'reveal':1.22,'jig':1.25,'bookcases':1.10,'apron':1.08,'bench':1.05,'stove':1.04,'wheel':1.07,'plinth':1.05,'back-wall':1.15,'lattice':1.13,'instruments':1.12}
