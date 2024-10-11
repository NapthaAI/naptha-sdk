import ast
import inspect
from naptha_sdk.package_manager import sort_modules, extract_dependencies
import os
from pathlib import Path
import sys
from typing import TypeVar
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

def scrape_init(file_path):
    def extract_value(value):
        if isinstance(value, ast.Constant):
            return value.value
        elif isinstance(value, ast.Name):
            return value.id
        elif isinstance(value, ast.Attribute):
            return f"{extract_value(value.value)}.{value.attr}"
        elif isinstance(value, ast.Call):
            if isinstance(value.func, ast.Attribute):
                return f"{extract_value(value.func.value)}.{value.func.attr}()"
            elif isinstance(value.func, ast.Name):
                return f"{value.func.id}()"
        else:
            return ast.unparse(value)

    with open(file_path, 'r') as file:
        tree = ast.parse(file.read(), filename=file_path)

    variables = []
    unique_variables = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        data = {"type": "call", "target": target.id, "cls_name": node.value.func.id}
                        if node.value.keywords:
                            data['keywords'] = [kw.arg for kw in node.value.keywords]
                            data['values'] = [extract_value(kw.value) for kw in node.value.keywords]
                        unique_variables[data['target']] = data
                    elif isinstance(node.value, ast.Constant):
                        data = {"type": "constant", "target": target.id, "value": node.value.value}
                        unique_variables[data['target']] = data

    # Convert the dictionary values back to a list
    variables = list(unique_variables.values())

    return variables

def get_obj_dependencies(context_globals, fn_code, processed=None):
    if processed is None:
        processed = set()

    modules = []
    for name, obj in context_globals.items():
        if name in fn_code and obj not in processed:
            if name.startswith("__"):
                continue

            processed.add(obj)  # Add the current object to the set of processed objects

            if inspect.ismodule(obj):
                obj_info = {
                    'name': name,
                    'module': obj.__name__,
                    'import_type': "standard",
                    'is_local': is_local_module(obj)
                }
                modules.append(obj_info)
            else:
                module = sys.modules.get(obj.__module__, None)
                if module and module not in processed:
                    is_local = is_local_module(module)
                    obj_info = {
                        'name': name,
                        'module': obj.__module__,
                        'import_type': "selective",
                        'is_local': is_local
                    }
                    if is_local:
                        if isinstance(obj, TypeVar):
                            obj_info['source'] = ""
                        else:
                            obj_info['source'] = inspect.getsource(obj)
                            modules.extend(get_obj_dependencies(module.__dict__, obj_info['source'], processed))
                    modules.append(obj_info)

    return modules

def scrape_func(func, variables):
    fn_code = inspect.getsource(func)
    fn_name = func.__name__
    fn_code = "\n".join(line for line in fn_code.splitlines() if not line.strip().startswith("@"))

    used_variables = []
    for variable in variables:
        if variable['target'] in fn_code:
            used_variables.append(variable)

    if inspect.isfunction(func):
        context_globals = func.__globals__
    elif inspect.isclass(func):
        module = sys.modules[func.__module__]
        context_globals = module.__dict__

    modules = get_obj_dependencies(context_globals, fn_code)

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
            # If the variable's class is not in modules, add it
            var_class = context_globals.get(used_variable['cls_name'])
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
                if any(module['name'] == used_variable['cls_name'] for module in modules):
                    class_info['import_needed'] = False
                modules.append(class_info)

    modules = [module for module in modules if module['name'] != 'logger']
    local_modules = [module for module in modules if module['is_local']]
    module_dependencies = {mod['name']: extract_dependencies(mod, local_modules) for mod in local_modules}
    local_modules = sort_modules(local_modules, module_dependencies) # Sort local modules based on dependencies
    selective_import_modules = [module for module in modules if not module['is_local'] and module['import_type'] == 'selective']
    standard_import_modules = [module for module in modules if module['import_type'] == 'standard']
    variable_modules = [module for module in modules if module['import_type'] == 'variable']

    return fn_code, fn_name, local_modules, selective_import_modules, standard_import_modules, variable_modules
