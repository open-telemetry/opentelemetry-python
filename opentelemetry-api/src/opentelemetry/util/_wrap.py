def patch_abc(abstract_base_class, method_name, w):
    """
    Patches a method on leaf subclasses of an abstract base class.

    """
    all_subclasses = recursively_get_all_subclasses(abstract_base_class)
    leaf_subclasses = get_leaf_subclasses(all_subclasses)

    for subclass in leaf_subclasses:
        # Patch if the subclass has the method (either defined or inherited)
        # and it's actually callable
        if hasattr(subclass, method_name) and callable(getattr(subclass, method_name)):
            old_method = getattr(subclass, method_name)
            setattr(subclass, method_name, w(old_method))

    # This implementation does not work if the instrumented class is imported after the instrumentor runs.
    # However, that case can be handled by querying the gc module for all existing classes; this capability can be added
    # in a follow-up change.


def get_leaf_subclasses(all_subclasses):
    """
    Returns only the leaf classes (classes with no subclasses) from a set of classes.
    """
    leaf_classes = set()
    for cls in all_subclasses:
        # A class is a leaf if no other class in the set is its subclass
        is_leaf = True
        for other_cls in all_subclasses:
            if other_cls != cls and issubclass(other_cls, cls):
                is_leaf = False
                break
        if is_leaf:
            leaf_classes.add(cls)
    return leaf_classes



def recursively_get_all_subclasses(cls):
    out = set()
    for subclass in cls.__subclasses__():
        out.add(subclass)
        out.update(recursively_get_all_subclasses(subclass))
    return out
