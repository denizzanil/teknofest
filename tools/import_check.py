import sys
sys.path.append('c:/Users/USER/Desktop/Dersler/4.sınıf bahar/TEKNOFEST')

try:
    import core.states as states
    import core.components as components
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_FAILED', e)
    raise
