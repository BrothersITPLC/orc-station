def has_custom_permission(view, model):
    action_permissions = {
        "create": f"add_{model}",
        "list": f"view_{model}",
        "update": f"change_{model}",
        "partial_update": f"change_{model}",
        "destroy": f"delete_{model}",
        "retrieve": f"view_{model}",
    }
    view.permission_required = action_permissions.get(view.action, None)
    return [permission() for permission in view.permission_classes]
