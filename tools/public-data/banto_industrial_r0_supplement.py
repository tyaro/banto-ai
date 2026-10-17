"""Additional binding/handle/clock semantics after first source audit."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import banto_industrial_r0_intake as intake
intake.PATHS=['crates/banto-tagclient/src/binding.rs','crates/banto-tagclient/src/handle.rs','crates/banto-tstore/src/clock.rs','crates/banto-tstore/src/reader.rs']
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();intake.main(a.output)
