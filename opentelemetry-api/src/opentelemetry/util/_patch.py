def patch_leaf_subclasses(base_class, method_name, wrapper):
    """
    Patches a method on leaf subclasses of a base class.

    Args:
        base_class: The base class whose leaf subclasses will be patched
        method_name: Name of the method to patch
        wrapper: Function that wraps the original method

    """
    all_subclasses = _get_all_subclasses(base_class)
    leaf_subclasses = _get_leaf_subclasses(all_subclasses)

    for subclass in leaf_subclasses:
        # Patch if the subclass has the method (either defined or inherited)
        # and it's actually callable
        if hasattr(subclass, method_name) and callable(getattr(subclass, method_name)):
            old_method = getattr(subclass, method_name)
            setattr(subclass, method_name, wrapper(old_method))

    # This implementation does not work if the instrumented class is imported after the instrumentor runs.


def _get_leaf_subclasses(all_subclasses):
    """
    Returns only the leaf classes (classes with no subclasses) from a set of classes.

    Args:
        all_subclasses: Set of classes to filter

    Returns:
        set: Classes that have no subclasses within the provided set
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


def _get_all_subclasses(cls):
    """
    Gets all subclasses of a given class.

    Args:
        cls: The base class to find subclasses for

    Returns:
        set: All subclasses (direct and indirect) of the given class
    """
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(_get_all_subclasses(subclass))
    return subclasses
