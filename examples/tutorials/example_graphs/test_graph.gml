graph [
  directed 1
  multigraph 1
  node [
    id 0
    label "node_0"
    name "node_0"
    type "block"
  ]
  node [
    id 1
    label "adder_2"
    name "adder_2"
    type "block"
  ]
  node [
    id 2
    label "node_1"
    name "node_1"
    type "block"
  ]
  node [
    id 3
    label "save_and_exit_3"
    name "save_and_exit_3"
    type "block"
  ]
  edge [
    source 0
    target 1
    key 0
    src ""
    type "Int32"
    dest "a"
  ]
  edge [
    source 1
    target 3
    key 0
    src ""
    type "Int32"
    dest "val"
  ]
  edge [
    source 2
    target 1
    key 0
    src ""
    type "Int32"
    dest "b"
  ]
]
