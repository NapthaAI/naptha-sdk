import ast
import inspect
import os
from pydantic import BaseModel
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

# def get_class_dependencies(cls):
#     dependencies = []
#     # Check if it's a Pydantic model
#     # if issubclass(cls, BaseModel):
#     #     print("Class is a pydantic model...")
#     #     args_schema = cls.model_fields.get('args_schema')
#     #     print("Args Schema: ", args_schema)
#             # field_type = field.annotation
#             # if inspect.isclass(field_type):
#             #     dependency = {
#             #         'name': field_type.__name__,
#             #         'module': field_type.__module__,
#             #         'is_local': is_local_module(sys.modules[field_type.__module__]),
#             #         'type': 'pydantic_field'
#             #     }
#             #     dependencies.append(dependency)

#     # # Check base classes
#     # for base in cls.__bases__:
#     #     if base != object and base != BaseModel:  # Exclude object and BaseModel
#     #         dependency = {
#     #             'name': base.__name__,
#     #             'module': base.__module__,
#     #             'is_local': is_local_module(sys.modules[base.__module__]),
#     #             'type': 'base_class'
#     #         }
#     #         dependencies.append(dependency)

#     class_source = inspect.getsource(cls)
#     class_ast = ast.parse(class_source)

#     dependencies = []
#     for node in ast.walk(class_ast):
#         if isinstance(node, ast.Name):
#             if not node.id in dir(builtins):
#                 # print('GGGGG', node, node.id, type(node.ctx).__name__, isinstance(node, ast.Import))
#                 dependency = {
#                     'name': node.id,
#                     'type': type(node.ctx).__name__
#                 }
#                 dependencies.append(dependency)

#     print(dependencies)

#     # Remove "Load" dependencies if a "Store" dependency with the same name exists
#     store_names = {dep['name'] for dep in dependencies if dep['type'] == 'Store'}
#     dependencies = [dep for dep in dependencies if not (dep['type'] == 'Load' and dep['name'] in store_names)]

#     # Keep only dependencies with type "Load"
#     dependencies = [dep for dep in dependencies if dep['type'] == 'Load']

#     print(dependencies)


#             # if node.id in sys.modules:
#             #     print(is_local_module(sys.modules[node.id]))
#             # # Check if the node represents a module
#             # if node.id in sys.modules:
#             #     module = sys.modules[node.id]
#             #     if is_local_module(module):
#             #         dependency = {
#             #             'name': node.id,
#             #             'module': module.__name__,
#             #             'is_local': True,
#             #             'type': 'local_module'
#             #         }
#             #         dependencies.append(dependency)


#     # for name, obj in cls.__dict__.items():
#     #     print("222222", name, obj)
#     #     if inspect.isclass(obj) and obj != cls:
#     #         dependency = {
#     #             'name': obj.__name__,
#     #             'module': obj.__module__,
#     #             'is_local': is_local_module(sys.modules[obj.__module__])
#     #         }
#     #         dependencies.append(dependency)
#     return dependencies

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

def scrape_code(func):
    print("FUNC", func)
    fn_code = inspect.getsource(func)

    func_globals = func.__globals__

    # Find classes used in the function
    modules = []
    seen = set()  # To keep track of unique modules
    for name, obj in func_globals.items():
        if inspect.isclass(obj) and name in inspect.getsource(func):
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

    local_modules = [module for module in modules if module['is_local']]
    selective_import_modules = [module for module in modules if not module['is_local'] and module['import_type'] != 'standard']
    standard_import_modules = [module for module in modules if module['import_type'] == 'standard']

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

    return fn_code, local_modules, selective_import_modules, standard_import_modules
