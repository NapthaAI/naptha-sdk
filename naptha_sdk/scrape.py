import inspect
import os
import sys

def is_local_module(module):
    if not hasattr(module, '__file__'):
        return False  # Built-in modules don't have __file__

    module_path = os.path.abspath(module.__file__)
    current_dir = os.path.abspath(os.getcwd())
    
    # Check if the module is in the current directory or its subdirectories
    if module_path.startswith(current_dir):
        # Check if the module is in the .venv directory
        venv_dir = os.path.join(current_dir, '.venv')
        if module_path.startswith(venv_dir):
            return False  # It's in .venv, so it's an installed package
        return True  # It's in the project directory, but not in .venv
    
    return False  # It's outside the project directory

def scrape_code(func):
    fn_code = inspect.getsource(func)

    func_globals = func.__globals__

    # Find classes used in the function
    local_modules = []
    installed_modules = []
    for name, obj in func_globals.items():
        if inspect.isclass(obj) and name in inspect.getsource(func):
            print()

            module = sys.modules[obj.__module__]
            is_local = is_local_module(module)

            class_info = {
                'name': name,
                'module': obj.__module__,
                'is_local': is_local
            }

            # Only get and store source code for local modules
            if is_local:
                class_info['source'] = inspect.getsource(obj)
                local_modules.append(class_info)
                print("222222", obj.__bases__)
            else:
                installed_modules.append(class_info)

    print(f"Classes used in {func.__name__}:")
    for cls in local_modules:
        source_type = "Local module" if cls['is_local'] else "Installed package"
        print(f"  {cls['name']} from {cls['module']} ({source_type})")
        if cls['is_local']:
            print(f"  Source code:\n{cls['source'][:100]}...\n")  # Truncated for brevity
    for cls in installed_modules:
        source_type = "Local module" if cls['is_local'] else "Installed package"
        print(f"  {cls['name']} from {cls['module']} ({source_type})")
        if cls['is_local']:
            print(f"  Source code:\n{cls['source'][:100]}...\n")  # Truncated for brevity

    return fn_code, local_modules, installed_modules