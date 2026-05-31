import sys
sys.path.append('e:/NJUD')
from generate_missing_txt import find_roster_file, DRIVE_ROOT, ROUTINE_EXTS
prog = '11'
year = '2025'
result = find_roster_file(prog, year)
print('Result path:', result)
if result:
    print('Exists?', result.exists())
    print('Suffix:', result.suffix)
    try:
        txt = result.read_text(encoding='utf-8', errors='ignore')
        print('Read text length:', len(txt))
        print('First 200 chars:', txt[:200])
    except Exception as e:
        print('Read error:', e)
        # Try binary read
        try:
            data = result.read_bytes()
            print('Binary length:', len(data))
        except Exception as e2:
            print('Binary read error:', e2)
