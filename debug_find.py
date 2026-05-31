import sys
sys.path.append('e:/NJUD')
from generate_missing_txt import find_roster_file, DRIVE_ROOT, ROUTINE_EXTS
prog = '11'
year = '2025'
result = find_roster_file(prog, year)
print('Result:', result)
if result:
    print('Exists?', result.exists())
    print('Suffix:', result.suffix)
    try:
        txt = result.read_text(encoding='utf-8')
        print('Content length:', len(txt))
    except Exception as e:
        print('Read error:', e)
