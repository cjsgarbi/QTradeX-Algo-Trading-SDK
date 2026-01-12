"""
INTERNAL REPLACEMENT FOR bitshares-signing (External Library)
-------------------------------------------------------------
This module replaces the external `bitshares-signing` library.
Reason: The external library required `secp256k1` which failed to compile on Windows without C++ tools.
Functionality: Re-implements critical signing (via coincurve) and RPC logic natively within the project.
"""
from .rpc import *
from .signing import broker, prototype_order
