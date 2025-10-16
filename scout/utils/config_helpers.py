from pathlib import Path
from typing import List, Union
from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig


def merge_configs(config_paths: List[Union[str, Path]]) -> DictConfig:
    """
    Merge multiple YAML configuration files with precedence. Later configs override earlier ones. Useful for applying overrides to base configs.

    Args:
        config_paths: List of paths to YAML config files. Later configs take precedence.

    Returns:
        DictConfig: Merged configuration object

    Raises:
        FileNotFoundError: If any config file doesn't exist

    Example:
        >>> config = merge_configs([ "config/default.yaml", "config/test.yaml"])
        >>> pipeline = FilterPipeline(config)
    """
    if not config_paths:
        raise ValueError("config_paths is empty!")

    # Load first config as base
    merged = OmegaConf.load(config_paths[0])

    # Merge remaining configs with precedence
    for config_path in config_paths[1:]:
        config = OmegaConf.load(config_path)
        merged = OmegaConf.unsafe_merge(merged, config)

    return merged

