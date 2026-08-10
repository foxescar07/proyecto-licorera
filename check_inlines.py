from django.contrib import admin
results = []
for model, admin_obj in admin.site._registry.items():
    for inline_class in getattr(admin_obj, "inlines", []):
        try:
            inline_class(model, admin_obj.admin_site).check()
        except Exception as e:
            results.append(f"ROTO: {inline_class.__name__} en {model.__name__} -> {e}")
print(results)
