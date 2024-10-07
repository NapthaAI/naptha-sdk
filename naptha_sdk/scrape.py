import ast
import inspect
import os
from pathlib import Path
from pydantic import BaseModel
import sys
import yaml

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

def get_class_dependencies(obj, module):
    modules = []
    for name, module_obj in module.__dict__.items():
        if name.startswith("__"):
            continue
        elif inspect.ismodule(module_obj):
            obj_info = {
                'name': name,
                'module': module_obj.__name__,
                'import_type': "standard",
                'is_local': is_local_module(module_obj)
            }
            modules.append(obj_info)
        else:
            is_local = is_local_module(sys.modules[module_obj.__module__])
            obj_info = {
                'name': name,
                'module': module_obj.__module__,
                'import_type': "selective",
                'is_local': is_local
            }
            if is_local:
                obj_info['source'] = inspect.getsource(module_obj) 
            modules.append(obj_info)

    return modules

def scrape_init(file_path):
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read(), filename=file_path)

    variables = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):                        
                        data = {"type": "call", "target": target.id, "cls_name":  node.value.func.id}

                        if node.value.keywords:
                            data['keywords'] = [kw.arg for kw in node.value.keywords]
                            values = []
                            for kw in node.value.keywords:
                                if isinstance(kw.value, ast.Constant):
                                    values.append(kw.value.value)
                                elif isinstance(kw.value, ast.Name):
                                    values.append(kw.value.id)
                                elif isinstance(kw.value, ast.Attribute):
                                    values.append(f"{kw.value.value.id}.{kw.value.attr}")
                                elif isinstance(kw.value, ast.Call):
                                    values.append(f"{kw.value.func.id}()")
                                else:
                                    values.append(ast.unparse(kw.value))
                            data['values'] = values
                    elif isinstance(node.value, ast.Constant):
                        data = {"type": "constant", "target": target.id, "value": node.value.value}
                    variables.append(data)

    print("Variables", variables)

    return variables

def scrape_func(func, variables):
    fn_code = inspect.getsource(func)

    # Remove lines that start with '@' (decorators)
    fn_code = "\n".join(line for line in fn_code.splitlines() if not line.strip().startswith("@"))
    print("FUNC", fn_code)


    used_variables = []
    for variable in variables:
        if variable['target'] in fn_code:
            used_variables.append(variable)

    func_globals = func.__globals__

    # Find classes used in the function
    modules = []
    seen = set()  # To keep track of unique modules
    for name, obj in func_globals.items():
        if inspect.isclass(obj) and name in fn_code:

            module = sys.modules[obj.__module__]
            is_local = is_local_module(module)

            class_info = {
                'name': name,
                'module': obj.__module__,
                'import_type': "selective",
                'is_local': is_local
            }

            # Check if this module has already been added
            module_key = (class_info['name'], class_info['module'])
            if module_key not in seen:
                seen.add(module_key)

                if is_local:
                    print(f"Module Name: {name}")
                    class_info['source'] = inspect.getsource(obj)
                    
                    # Also get dependencies of the local module
                    add_modules = get_class_dependencies(obj, module)
                    for add_module in add_modules:
                        add_key = (add_module['name'], add_module['module'])
                        if add_key not in seen:
                            seen.add(add_key)
                            modules.append(add_module)

                modules.append(class_info)

    # Deal with variables from the main file
    for used_variable in used_variables:
        if used_variable['type'] == 'constant':
            cwd = Path.cwd()
            full_path = Path(f"src/{cwd.name}/{used_variable['value']}")
            if full_path.exists():
                with open(full_path, 'r') as file:
                    yaml_data = yaml.safe_load(file)
                line = f"{used_variable['target']} = {yaml_data}\n"
                class_info = {
                    'name': used_variable['target'],
                    'module': None,
                    'import_type': "variable",
                    'is_local': False
                }
                class_info['source'] = line
                modules.append(class_info)

        elif used_variable['type'] == 'call':
            # if the class is already in modules, skip it
            if any(module['name'] == used_variable['cls_name'] for module in modules):
                continue
            # If the variable's class is not in modules, add it
            var_class = func_globals.get(used_variable['cls_name'])
            if var_class and inspect.isclass(var_class):
                module = sys.modules[var_class.__module__]
                class_info = {
                    'name': used_variable['cls_name'],
                    'module': var_class.__module__,
                    'import_type': "variable",
                    'is_local': False
                }
                line = f"{used_variable['target']} = {used_variable['cls_name']}("
                for kw, value in zip(used_variable['keywords'], used_variable['values']):
                    if isinstance(value, str):
                        line += f"{kw}='{value}', "
                    else:
                        line += f"{kw}={value}, "
                line += ")\n"
                class_info['source'] = line
                modules.append(class_info)

    local_modules = [module for module in modules if module['is_local']]
    selective_import_modules = [module for module in modules if not module['is_local'] and module['import_type'] == 'selective']
    standard_import_modules = [module for module in modules if module['import_type'] == 'standard']
    variable_modules = [module for module in modules if module['import_type'] == 'variable']

    print(f"Classes and modules used in {func.__name__}:")
    
    print("Local modules:")
    for cls in local_modules:
        print(f"  {cls['name']} from {cls['module']} (Local module)")
        print(f"  Source code:\n{cls['source'][:100]}...\n")  # Truncated for brevity
    
    print("Selective import packages:")
    for cls in selective_import_modules:
        print(f"  {cls['name']} from {cls['module']} (Selective import package)")
    
    print("Standard import packages:")
    for cls in standard_import_modules:
        print(f"  {cls['name']} from {cls['module']} (Standard import package)")
    
    print("Variable modules:")
    for cls in variable_modules:
        print(f"  {cls['name']} from {cls['module']} (Variable module)")
        print(f"  Source code:\n{cls['source'][:100]}...\n")  # Truncated for brevity

    return fn_code, local_modules, selective_import_modules, standard_import_modules, variable_modules
