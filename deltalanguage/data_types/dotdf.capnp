@0xbbc993b6190096ff; # unique file ID, generated by `capnp id`

struct Program {
  name @0 :Text;
  bodies @1 :List(Body);
  nodes @2 :List(Node);
  # Adjacency list from (NodeIdx, OutPortIdx) to (NodeIdx, InPortIdx).
  graph @3 :List(Wire);
  files @4 :Data; # Data for a ZIP file.
  requirements @5 :List(Text);
}

struct Wire {
  srcNode @0 :UInt32;
  srcOutPort @1 :UInt32;
  destNode @2 :UInt32;
  destInPort @3 :UInt32;
  direct @4 :Bool; # A minimum-sized buffer is requested for this wire.
}

struct Node {
  # node id is given by position in the nodes list in the outer Program.
  name @0 :Text;
  bodies @1 :List(Int32); # indices reference the bodies list in the outer Program
  inPorts @2 :List(InPort); # instantaneous port types
  outPorts @3 :List(OutPort);
}

struct Body {
  # we seperate bodies from the nodes as reusing a element of functionality is
  # likely to be common, and we should maintain the user intent.
  union {
    python :group {
      dillImpl @0 :Data;
    }
    migen :union {
      verilog @1 :Text;
      dillImpl @2 :Data; # partial func to generate the Migennode
    }
    interactive :group {
      dillImpl @3 :Data;
    }
  }
}

struct InPort {
  name @0 :Text; # Lookip id for the port: kwarg in Pynodes, signal name in Migen
  type @1 :Data; # Delta Type as serialsed by dill
  optional @2 :Bool; # only InPort can be optional
}

struct OutPort {
  name @0 :Text; # Lookip id for the port: kwarg in Pynodes, signal name in Migen
  type @1 :Data; # Delta Type as serialsed by dill
}
