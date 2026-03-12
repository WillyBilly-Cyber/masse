# B3: 3D Single-Story Frame - Diaphragm Flexibility + Torsion
# Rectangular plan 120ft x 80ft, 4 perimeter frames
# Compare rigid vs semi-rigid diaphragm behavior

model BasicBuilder -ndm 3 -ndf 6

# Plan dimensions
set Lx 120.0
set Ly 80.0
set H 15.0

# Create corner columns
node 1 0 0 0
node 2 $Lx 0 0
node 3 $Lx $Ly 0
node 4 0 $Ly 0

# Roof nodes (same X/Y, at height)
node 11 0 0 $H
node 12 $Lx 0 $H
node 13 $Lx $Ly $H
node 14 0 $Ly $H

# Fix base
fix 1 1 1 1 1 1 1
fix 2 1 1 1 1 1 1
fix 3 1 1 1 1 1 1
fix 4 1 1 1 1 1 1

# Elastic material
uniaxialMaterial Elastic 1 29000.0

# Column sections
section Elastic 1 29000.0 50.0 500.0

# Columns
geomTransf Linear 1 0 0 1
element elasticBeamColumn 1 1 11 1 1
element elasticBeamColumn 2 2 12 1 1
element elasticBeamColumn 3 3 13 1 1
element elasticBeamColumn 4 4 14 1 1

# Roof beams (perimeter)
geomTransf Linear 2 0 0 1
element elasticBeamColumn 5 11 12 1 1
element elasticBeamColumn 6 12 13 1 1
element elasticBeamColumn 7 13 14 1 1
element elasticBeamColumn 8 14 11 1 1

# Mass (lumped at roof CM)
set totalMass 50.0
node 100 [expr $Lx/2.0] [expr $Ly/2.0] $H
mass 100 $totalMass $totalMass $totalMass 0 0 0

# Rigid diaphragm constraint (all roof nodes to CM)
rigidDiaphragm 3 100 11 12 13 14

# Lateral load with eccentricity (torsion)
pattern Plain 1 Linear {
    load 100 10.0 5.0 0 0 0 0
}

# Recorder: roof drift at corner 11
recorder Node -file B3_drift_node11.out -timeStep -node 11 -dof 1 disp
recorder Node -file B3_drift_node12.out -timeStep -node 12 -dof 1 disp
recorder Node -file B3_rot.out -timeStep -node 100 -dof 6 disp

# Analysis
system UmfPack
numberer RCM
constraints Plain
test NormDispIncr 1.0e-6 30
algorithm Newton
integrator LoadControl 1.0
analyze 10

puts "B3 diaphragm analysis completed"
