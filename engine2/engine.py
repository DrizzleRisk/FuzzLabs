#!/usr/bin/env python

import json
import inspect
import importlib
from utils import utils
from logic.Linear import Linear

# =============================================================================
#
# =============================================================================

def read_packet_grammar(filename):
    data = utils.read_file(filename)
    return utils.from_json(data)

# =============================================================================
#
# =============================================================================

def init_root(grammar):
    root       = None
    logic      = grammar.get('logic')
    transforms = grammar.get('transforms')
    properties = grammar.get('properties')

    try:
        root = getattr(importlib.import_module("primitives.block"), "block")(
                   properties, transforms, logic)
    except Exception, ex:
        print "failed to instantiate root block (%s)" % str(ex)
    return root

# =============================================================================
#
# =============================================================================

if __name__ == "__main__":
    root = init_root(read_packet_grammar("./packet.json"))

    if root == None:
        raise Exception("failed to initialize root block")

    # We always apply linear logic on the root element.
    for iteration in Linear(root).run():
        print iteration

