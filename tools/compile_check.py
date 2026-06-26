import py_compile
files = ['core/states.py', 'core/components.py', 'gui.py']
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'{f}: OK')
    except py_compile.PyCompileError as e:
        print(f'{f}: COMPILE_ERROR')
        print(e.msg)
    except Exception as e:
        print(f'{f}: EXCEPTION {e}')
