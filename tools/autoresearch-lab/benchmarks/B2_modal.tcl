# B2: 2D Steel Moment Frame - Modal Analysis
# Same geometry as B1, eigen extraction only

model BasicBuilder -ndm 2 -ndf 3

# Geometry
set Lb 30.0
set Hs 12.0
set nStories 3
set nBays 3

# Nodes
set nodeTag 1
for {set i 0} {$i <= $nBays} {incr i} {
    for {set j 0} {$j <= $nStories} {incr j} {
        set x [expr $i * $Lb]
        set y [expr $j * $Hs]
        node $nodeTag $x $y
        incr nodeTag
    }
}

# Fixity
foreach baseNode {1 5 9 13} {
    fix $baseNode 1 1 1
}

# Material
uniaxialMaterial Elastic 1 29000.0

# Section
section Elastic 1 29000.0 100.0 1000.0

# Columns
geomTransf Linear 1
element elasticBeamColumn 1 1 2 1 1
element elasticBeamColumn 2 5 6 1 1
element elasticBeamColumn 3 9 10 1 1
element elasticBeamColumn 4 2 3 1 1
element elasticBeamColumn 5 6 7 1 1
element elasticBeamColumn 6 10 11 1 1

# Beams
element elasticBeamColumn 7 2 5 1 1
element elasticBeamColumn 8 3 6 1 1
element elasticBeamColumn 9 4 7 1 1
element elasticBeamColumn 10 6 9 1 1
element elasticBeamColumn 11 7 10 1 1
element elasticBeamColumn 12 8 11 1 1
element elasticBeamColumn 13 10 13 1 1
element elasticBeamColumn 14 11 14 1 1
element elasticBeamColumn 15 12 15 1 1

# Mass (lumped)
set massPerFloor 10.0
foreach floorNode {4 8 12} {
    mass $floorNode $massPerFloor 0 0
}

# Eigen
set numModes 3
set lambda [eigen $numModes]

# Periods
set T1 [expr 2*3.1415926535/sqrt([lindex $lambda 0])]
set T2 [expr 2*3.1415926535/sqrt([lindex $lambda 1])]
set T3 [expr 2*3.1415926535/sqrt([lindex $lambda 2])]

# Write periods to file for machine parsing
set fp [open "B2_periods.out" "w"]
puts $fp "T1 $T1"
puts $fp "T2 $T2"
puts $fp "T3 $T3"
close $fp

puts "B2 modal analysis completed"
