import ast
import os

productos_file = r"c:\Users\SENA\Documents\GitHub\proyecto-licorera\productos\views.py"
inventario_file = r"c:\Users\SENA\Documents\GitHub\proyecto-licorera\inventario\views.py"

def extract_functions(filepath, func_names):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    lines = source.split('\n')
    tree = ast.parse(source)
    
    extracted = {}
    ranges_to_remove = []
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in func_names:
            start = node.lineno - 1
            # find decorators
            if node.decorator_list:
                start = node.decorator_list[0].lineno - 1
            
            end = node.end_lineno
            
            # extract
            func_lines = lines[start:end]
            extracted[node.name] = "\n".join(func_lines) + "\n\n"
            ranges_to_remove.append((start, end))
            
    # Remove from bottom to top to not mess up line numbers
    ranges_to_remove.sort(reverse=True)
    for start, end in ranges_to_remove:
        # Also remove any preceding comments for the function (simple heuristic: look for # ======)
        # We won't remove comments to be safe, just the function and its decorators
        del lines[start:end]
        
    return extracted, "\n".join(lines)

# Functions to move P -> I
p_to_i_names = ["stock_status", "producto_salida", "rotacion_json", "agenda_lista", "agenda_eliminar"]
# Functions to move I -> P
i_to_p_names = ["gestion_productos", "gestion_producto_editar", "gestion_producto_eliminar", 
                "gestion_categoria_crear", "gestion_categoria_editar", "gestion_categoria_eliminar"]

p_extracted, new_p_source = extract_functions(productos_file, p_to_i_names)
i_extracted, new_i_source = extract_functions(inventario_file, i_to_p_names)

# In inventario/views.py, there's already a stock_status. We need to decide which one to keep.
# Let's keep the one from productos/views.py as it seems more updated with URL reversing.
# So we must remove the existing stock_status from inventario too!
i_extracted_extra, new_i_source = extract_functions(inventario_file, ["stock_status"] + i_to_p_names)

# Assemble new productos/views.py
with open(productos_file, 'w', encoding='utf-8') as f:
    f.write(new_p_source)
    f.write("\n# ===============================\n# FUNCIONES MOVIDAS DESDE INVENTARIO\n# ===============================\n")
    for name in i_to_p_names:
        if name in i_extracted_extra:
            f.write(i_extracted_extra[name])

# Assemble new inventario/views.py
with open(inventario_file, 'w', encoding='utf-8') as f:
    f.write(new_i_source)
    f.write("\n# ===============================\n# FUNCIONES MOVIDAS DESDE PRODUCTOS\n# ===============================\n")
    for name in p_to_i_names:
        if name in p_extracted:
            f.write(p_extracted[name])

print("Refactor complete.")
