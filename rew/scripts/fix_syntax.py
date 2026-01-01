import re

with open('main3.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace except blocks with only comments with except block + pass
pattern = r'(except [^:]*:)\s*# [^\n]*\n'
replacement = r'\1\n                        pass\n'

content = re.sub(pattern, replacement, content)

with open('main3.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed except blocks")
