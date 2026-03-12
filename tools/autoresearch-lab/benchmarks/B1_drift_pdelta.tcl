# B1: 2D Steel Moment Frame - Drift + P-Delta Pushover
# 3-story, 3-bay, elastic columns/beams (baseline)
# Units: kip-ft-sec

model BasicBuilder -ndm 2 -ndf 3

# Geometry
set Lb 30.0   ;# bay width (ft)
set Hs 12.0   ;# story height (ft)
set nStories 3
set nBays 3

# Create nodes
set nodeTag 1
for {set i 0} {$i <= $nBays} {incr i} {
    for {set j 0} {$j <= $nStories} {incr j} {
        set x [expr $i * $Lb]
        set y [expr $j * $Hs]
        node $nodeTag $x $y
        incr nodeTag
    }
}

# Support fixity (base nodes: 1, 5, 9, 13 for 3 bays)
foreach baseNode {1 5 9 13} {
    fix $baseNode 1 1 1
}

# Elastic materials
uniaxialMaterial Elastic 1 29000.0  ;# steel E (ksi)

# Section: elastic (placeholder, adjust via spec)
section Elastic 1 29000.0 100.0 1000.0

# Columns (exterior)
geomTransf PDelta 1
element elasticBeamColumn 1 1 2 1 1
element elasticBeamColumn 2 5 6 1 1
element elasticBeamColumn 3 9 10 1 1

# Columns (interior)
element elasticBeamColumn 4 2 3 1 1
element elasticBeamColumn 5 6 7 1 1
element elasticBeamColumn 6 10 11 1 1

# Beams (first story)
element elasticBeamColumn 7 2 5 1 1
element elasticBeamColumn 8 3 6 1 1
element elasticBeamColumn 9 4 7 1 1

# Beams (second story)
element elasticBeamColumn 10 6 9 1 1
element elasticBeamColumn 11 7 10 1 1
element elasticBeamColumn 12 8 11 1 1

# Beams (third story)
element elasticBeamColumn 13 10 13 1 1
element elasticBeamColumn 14 11 14 1 1
element elasticBeamColumn 15 12 15 1 1

# Mass (lumped at floor nodes, simplified)
set massPerFloor 10.0
foreach floorNode {4 8 12} {
    mass $floorNode $massPerFloor 0 0
}

# Boundary: P-Delta already in geomTransf

# Recorder: drifts (roof node 16 vs base)
recorder Drift -file B1_drift.out -timeStep -precision 10 \
    -nidN 16 -dofN 1 -nidN2 13 -dofN2 1 -pert 1

# Recorder: base shear (reaction at base nodes)
recorder Reaction -file B1_reaction.out -timeStep -node 1 5 9 13 -dof 1

# Analysis setup (to be overridden by MASSE/spec)
system UmfPack
numberer RCM
constraints Plain
test NormDispIncr 1.0e-6 30 0
algorithm Newton
integrator LoadControl 0.1

# Gravity (placeholder)
pattern Plain 1 Linear {
    eleLoad -ele 7 8 9 -type -beamUniform 0.5
    eleLoad -ele 10 11 12 -type -beamUniform 0.5
    eleLoad -ele 13 14 15 -type -beamUniform 0.5
}

analyze 10

# Reset for pushover
loadConst -time 0.0

# Pushover: lateral load pattern
pattern Plain 2 Linear {
    load 4 10.0 0 0
    load 8 15.0 0 0
    load 12 20.0 0 0
}

# Pushover analysis (displacement control at roof)
integrator DisplacementControl 12 1 0.1
analyze 20

puts "B1 pushover completed"
