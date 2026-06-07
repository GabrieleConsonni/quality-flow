def update_entity(entity, **kwargs):
    for key, value in kwargs.items():
        if hasattr(entity, key) and value is not None:
            setattr(entity, key, value)