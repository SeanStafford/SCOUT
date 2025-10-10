"""
General utility functions for SCOUT.

Contains helper functions used across different modules.
"""

import collections.abc


def flatten_dict(
    d_in,
    d_out="dontchangeme",
    key_min_parent_level=0,
    key_max_parents=0,
    key_path=[],
    key_delimiter="_",
):
    """
    Recursively flatten a nested dictionary.

    Inspired by: https://stackoverflow.com/a/6027615

    Args:
        d_in: Input dictionary to flatten
        d_out: Output dictionary (for recursion)
        key_min_parent_level: Minimum parent level to include in keys
        key_max_parents: Maximum number of parent levels to include in keys
        key_path: Current path through nested structure (for recursion)
        key_delimiter: Character(s) to join nested keys

    Returns:
        Flattened dictionary

    Example:
        >>> flatten_dict({"a": {"b": {"c": 1}}})
        {"a_b_c": 1}
    """
    if d_out == "dontchangeme":
        d_out = {}

    for k, v in d_in.items():
        key_path_temp = key_path + [k]
        if isinstance(v, collections.abc.MutableMapping):
            d_out = flatten_dict(
                v,
                d_out,
                key_min_parent_level,
                key_max_parents,
                key_path_temp,
                key_delimiter=key_delimiter,
            )
        else:
            hierarchical_key_child = key_path_temp.pop(-1)
            parent_level = min(
                len(key_path_temp),
                max(key_min_parent_level, len(key_path_temp) - key_max_parents),
            )
            hierarchical_key_i = key_delimiter.join(
                key_path_temp[parent_level:] + [hierarchical_key_child]
            )
            if hierarchical_key_i in d_out.keys():
                duplicate_key_error_message = (
                    f"Error while trying to flatten dictionary. "
                    f"Attempted to create more than one entry with key '{hierarchical_key_i}'."
                )
                raise KeyError(duplicate_key_error_message)
            else:
                d_out[hierarchical_key_i] = v
    return d_out
