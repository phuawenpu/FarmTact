"""Create an ignored development database secret without displaying it."""
from pathlib import Path
import os,secrets
p=Path('.env')
if not p.exists():
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write('FARMTACT_DB_PASSWORD='+secrets.token_hex(24)+'\n')
print('Development environment file ready; secret values are not displayed.')
