# save as fix_imports.py, run: python fix_imports.py
import os, re

for fname in os.listdir('.'):
    if not fname.endswith('.py'):
        continue
    with open(fname, 'r') as f:
        content = f.read()
    content = re.sub(r'from \.(\w)', r'from \1', content)   # from parser import X  →  from parser import X
    content = re.sub(r'from \. import', r'import', content)   # import models   →  import models
    with open(fname, 'w') as f:
        f.write(content)
    print(f"Fixed: {fname}")