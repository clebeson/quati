import sys
from pathlib import Path
r=sys.argv[1]; sys.path.insert(0,r+'/src')
import quati.behavior.contracts as c
print(r[-6:], c.asset_digest(Path(r)), c.__file__)
