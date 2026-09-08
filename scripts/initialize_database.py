from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.api.store import Store
Store()
print('Database schema and tenant foreign-key migration ready.')
