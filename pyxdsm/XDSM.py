"""
pyXDSM with Pydantic models for validation and serialization
"""

from __future__ import print_function
import os
import numpy as np
import json
from typing import Literal, Optional, Tuple, List, Dict, Set, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import plotly.graph_objects as go

from pyxdsm.xdsm_latex_writer import XDSMLatexWriter

# Constants
OPT = "Optimization"
SUBOPT = "SubOptimization"
SOLVER = "MDA"
DOE = "DOE"
IFUNC = "ImplicitFunction"
FUNC = "Function"
GROUP = "Group"
IGROUP = "ImplicitGroup"
METAMODEL = "Metamodel"
LEFT = "left"
RIGHT = "right"

# Type definitions - these match the TikZ styles in diagram_styles
NodeType = Literal['Optimization', 'SubOptimization', 'MDA', 'DOE', 'ImplicitFunction', 
                   'Function', 'Group', 'ImplicitGroup', 'Metamodel']
ConnectionStyle = Literal['DataInter', 'DataIO']
Side = Literal['left', 'right']
AutoFadeOption = Literal['all', 'connected', 'none', 'incoming', 'outgoing']

# Valid TikZ node styles (from diagram_styles.tikzstyles)
VALID_NODE_STYLES = {
    'Optimization', 'SubOptimization', 'MDA', 'DOE', 'ImplicitFunction',
    'Function', 'Group', 'ImplicitGroup', 'Metamodel', 'DataInter', 'DataIO'
}


class SystemNode(BaseModel):
    """System node on the diagonal of XDSM diagram."""

    node_name: str = Field(..., description="Unique name for the system")
    style: str = Field(..., description="Type/style of the system")
    label: Union[str, List[str], Tuple[str, ...]] = Field(..., description="Display label")
    stack: bool = Field(default=False, description="Display as stacked rectangles")
    faded: bool = Field(default=False, description="Fade the component")
    label_width: Optional[int] = Field(default=None, description="Number of items per line")
    spec_name: Optional[str] = Field(default=None, description="Name for spec file")
    subsystem: Optional['XDSM'] = Field(default=None, description="Nested XDSM for groups")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator('node_name')
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node name cannot be empty")
        return v.strip()

    @field_validator('style')
    @classmethod
    def validate_style(cls, v: str) -> str:
        """Validate that style is a known TikZ style."""
        if v not in VALID_NODE_STYLES:
            raise ValueError(
                f"Style '{v}' is not a valid TikZ style. "
                f"Valid styles are: {', '.join(sorted(VALID_NODE_STYLES))}"
            )
        return v

    def __init__(self, **data):
        super().__init__(**data)
        if self.spec_name is None:
            self.spec_name = self.node_name


class InputNode(BaseModel):
    """Input node at top of XDSM diagram."""
    
    node_name: str = Field(..., description="Internal node name")
    label: Union[str, List[str], Tuple[str, ...]] = Field(..., description="Display label")
    label_width: Optional[int] = Field(default=None, description="Number of items per line")
    style: str = Field(default="DataIO", description="Node style")
    stack: bool = Field(default=False, description="Display as stacked rectangles")
    faded: bool = Field(default=False, description="Fade the component")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputNode(BaseModel):
    """Output node on left or right side of XDSM diagram."""
    
    node_name: str = Field(..., description="Internal node name")
    label: Union[str, List[str], Tuple[str, ...]] = Field(..., description="Display label")
    label_width: Optional[int] = Field(default=None, description="Number of items per line")
    style: str = Field(default="DataIO", description="Node style")
    stack: bool = Field(default=False, description="Display as stacked rectangles")
    faded: bool = Field(default=False, description="Fade the component")
    side: Side = Field(..., description="Which side (left or right)")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ['left', 'right']:
            raise ValueError("Side must be 'left' or 'right'")
        return v


class ConnectionEdge(BaseModel):
    """Connection between two nodes."""
    
    src: str = Field(..., description="Source node name")
    target: str = Field(..., description="Target node name")
    label: Union[str, List[str], Tuple[str, ...]] = Field(..., description="Connection label")
    label_width: Optional[int] = Field(default=None, description="Number of items per line")
    style: str = Field(default="DataInter", description="Connection style")
    stack: bool = Field(default=False, description="Display as stacked")
    faded: bool = Field(default=False, description="Fade the connection")
    src_faded: bool = Field(default=False, description="Source node is faded")
    target_faded: bool = Field(default=False, description="Target node is faded")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('label_width')
    @classmethod
    def validate_label_width(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not isinstance(v, int):
            raise ValueError("label_width must be an integer")
        return v
    
    @model_validator(mode='after')
    def validate_no_self_connection(self):
        if self.src == self.target:
            raise ValueError("Cannot connect component to itself")
        return self


class ProcessChain(BaseModel):
    """Process flow chain between systems."""

    systems: List[str] = Field(..., description="List of system names in order")
    arrow: bool = Field(default=True, description="Show arrows on process lines")
    faded: bool = Field(default=False, description="Fade the process chain")

    @field_validator('systems')
    @classmethod
    def validate_systems(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("Process chain must contain at least 2 systems")
        return v


class AutoFadeConfig(BaseModel):
    """Configuration for automatic fading of components."""
    
    inputs: AutoFadeOption = Field(default='none', description="Auto-fade inputs")
    outputs: AutoFadeOption = Field(default='none', description="Auto-fade outputs")
    connections: AutoFadeOption = Field(default='none', description="Auto-fade connections")
    processes: AutoFadeOption = Field(default='none', description="Auto-fade processes")
    
    @field_validator('inputs', 'outputs', 'processes')
    @classmethod
    def validate_basic_options(cls, v: str) -> str:
        valid = ['all', 'connected', 'none']
        if v not in valid:
            raise ValueError(f"Must be one of {valid}")
        return v
    
    @field_validator('connections')
    @classmethod
    def validate_connection_options(cls, v: str) -> str:
        valid = ['all', 'connected', 'none', 'incoming', 'outgoing']
        if v not in valid:
            raise ValueError(f"Must be one of {valid}")
        return v


class XDSM(BaseModel):
    """
    XDSM diagram specification and renderer using Pydantic validation.
    """
    
    systems: List[SystemNode] = Field(default_factory=list, description="System nodes")
    connections: List[ConnectionEdge] = Field(default_factory=list, description="Connections")
    inputs: Dict[str, InputNode] = Field(default_factory=dict, description="Input nodes")
    outputs: Dict[str, OutputNode] = Field(default_factory=dict, description="Left output nodes")
    processes: List[ProcessChain] = Field(default_factory=list, description="Process chains")

    use_sfmath: bool = Field(default=True, description="Use sfmath LaTeX package")
    optional_packages: List[str] = Field(default_factory=list, description="Additional LaTeX packages")
    auto_fade: AutoFadeConfig = Field(default_factory=AutoFadeConfig, description="Auto-fade configuration")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, use_sfmath: bool = True, 
                 optional_latex_packages: Optional[Union[str, List[str]]] = None,
                 auto_fade: Optional[Dict[str, str]] = None,
                 **data):
        """
        Initialize XDSM object.

        Parameters
        ----------
        use_sfmath : bool
            Whether to use the sfmath latex package
        optional_latex_packages : str or list of strings
            Additional latex packages for PDF/TEX generation
        auto_fade : dict
            Auto-fade configuration with keys: inputs, outputs, connections, processes
        """
        # Only process if these aren't already in data (from deserialization)
        if 'optional_packages' not in data:
            # Process optional packages
            packages = []
            if optional_latex_packages is not None:
                if isinstance(optional_latex_packages, str):
                    packages = [optional_latex_packages]
                elif isinstance(optional_latex_packages, list):
                    packages = optional_latex_packages
                else:
                    raise ValueError("optional_latex_packages must be a string or list of strings")
            data['optional_packages'] = packages
        
        if 'auto_fade' not in data:
            # Process auto_fade
            fade_config = AutoFadeConfig()
            if auto_fade is not None:
                fade_config = AutoFadeConfig(**auto_fade)
            data['auto_fade'] = fade_config
        
        if 'use_sfmath' not in data:
            data['use_sfmath'] = use_sfmath
        
        super().__init__(**data)

    @model_validator(mode='before')
    @classmethod
    def set_defaults_for_missing_fields(cls, data):
        """Ensure missing or null collection fields get empty defaults."""
        if not isinstance(data, dict):
            return data

        # Set empty defaults for missing or null collection fields
        if 'inputs' not in data or data.get('inputs') is None:
            data['inputs'] = {}
        if 'outputs' not in data or data.get('outputs') is None:
            data['outputs'] = {}
        if 'systems' not in data or data.get('systems') is None:
            data['systems'] = []
        if 'connections' not in data or data.get('connections') is None:
            data['connections'] = []
        if 'processes' not in data or data.get('processes') is None:
            data['processes'] = []

        return data

    @model_validator(mode='after')
    def validate_unique_system_names(self):
        """Ensure all system names are unique."""
        names = [sys.node_name for sys in self.systems]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            raise ValueError(f"Duplicate system names: {set(duplicates)}")
        return self

    def get_flattened_systems(self, prefix: str = '') -> List[SystemNode]:
        """
        Get a flattened list of all systems, recursively expanding nested XDSM groups.

        This method traverses the system hierarchy and returns all leaf systems
        (systems without subsystems) with their node names prefixed by their parent
        group names using dot notation (e.g., 'group.subsystem').

        Parameters
        ----------
        prefix : str
            The prefix to prepend to system node names (used internally for recursion)

        Returns
        -------
        List[SystemNode]
            Flattened list of all leaf system nodes with prefixed names
        """
        flattened = []

        for sys in self.systems:
            if sys.subsystem is not None:
                # This is a group - recursively flatten it
                subsystem_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."
                flattened.extend(sys.subsystem.get_flattened_systems(prefix=subsystem_prefix))
            else:
                # This is a leaf system - add it with the prefix
                if prefix:
                    # Create a new SystemNode with the prefixed name
                    flattened_sys = SystemNode(
                        node_name=f"{prefix}{sys.node_name}",
                        style=sys.style,
                        label=sys.label,
                        stack=sys.stack,
                        faded=sys.faded,
                        label_width=sys.label_width,
                        spec_name=sys.spec_name,
                        subsystem=None
                    )
                    flattened.append(flattened_sys)
                else:
                    # Top-level system - add as-is
                    flattened.append(sys)

        return flattened

    def get_flattened_connections(self, prefix: str = '') -> List[ConnectionEdge]:
        """
        Get a flattened list of all connections, recursively expanding nested XDSM groups.

        This method collects connections from all levels of the hierarchy and prefixes
        the source and target node names appropriately.

        Parameters
        ----------
        prefix : str
            The prefix to prepend to node names (used internally for recursion)

        Returns
        -------
        List[ConnectionEdge]
            Flattened list of all connections with prefixed node names
        """
        flattened = []

        # Add connections from this level
        for conn in self.connections:
            if prefix:
                # Create a new ConnectionEdge with prefixed names
                prefixed_conn = ConnectionEdge(
                    src=f"{prefix}{conn.src}" if not conn.src.startswith(prefix) else conn.src,
                    target=f"{prefix}{conn.target}" if not conn.target.startswith(prefix) else conn.target,
                    label=conn.label,
                    label_width=conn.label_width,
                    style=conn.style,
                    stack=conn.stack,
                    faded=conn.faded,
                    src_faded=conn.src_faded,
                    target_faded=conn.target_faded
                )
                flattened.append(prefixed_conn)
            else:
                # Top-level connection - add as-is
                flattened.append(conn)

        # Recursively add connections from subsystems
        for sys in self.systems:
            if sys.subsystem is not None:
                subsystem_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."
                flattened.extend(sys.subsystem.get_flattened_connections(prefix=subsystem_prefix))

        return flattened

    def get_flattened_inputs(self, prefix: str = '') -> Dict[str, InputNode]:
        """
        Get a flattened dictionary of all inputs, recursively expanding nested XDSM groups.

        Parameters
        ----------
        prefix : str
            The prefix to prepend to system names (used internally for recursion)

        Returns
        -------
        Dict[str, InputNode]
            Flattened dictionary of inputs with prefixed system names as keys
        """
        flattened = {}

        # Add inputs from this level
        for sys_name, input_node in self.inputs.items():
            key = f"{prefix}{sys_name}" if prefix else sys_name
            flattened[key] = input_node

        # Recursively add inputs from subsystems
        for sys in self.systems:
            if sys.subsystem is not None:
                subsystem_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."
                flattened.update(sys.subsystem.get_flattened_inputs(prefix=subsystem_prefix))

        return flattened

    def get_flattened_outputs(self, prefix: str = '') -> Dict[str, OutputNode]:
        """
        Get a flattened dictionary of all outputs, recursively expanding nested XDSM groups.

        Parameters
        ----------
        prefix : str
            The prefix to prepend to system names (used internally for recursion)

        Returns
        -------
        Dict[str, OutputNode]
            Flattened dictionary of outputs with prefixed system names as keys
        """
        flattened = {}

        # Add outputs from this level
        for sys_name, output_node in self.outputs.items():
            key = f"{prefix}{sys_name}" if prefix else sys_name
            flattened[key] = output_node

        # Recursively add outputs from subsystems
        for sys in self.systems:
            if sys.subsystem is not None:
                subsystem_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."
                flattened.update(sys.subsystem.get_flattened_outputs(prefix=subsystem_prefix))

        return flattened

    def get_group_info(self) -> List[Dict[str, any]]:
        """
        Get information about groups and which systems belong to each group.

        Returns
        -------
        List[Dict[str, any]]
            List of dictionaries containing group information:
            - 'name': Group node name
            - 'label': Group label
            - 'systems': List of flattened system names in this group
            - 'depth': Nesting depth (0 for top-level groups)
            - 'is_expanded': True if group is expanded (showing subsystems)
        """
        groups = []

        def collect_groups(xdsm_instance, prefix='', depth=0):
            for sys in xdsm_instance.systems:
                if sys.subsystem is not None:
                    # This is a group
                    group_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."
                    full_group_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name

                    # Get all systems in this group
                    group_systems = []
                    for subsys in sys.subsystem.get_flattened_systems(prefix=group_prefix):
                        group_systems.append(subsys.node_name)

                    groups.append({
                        'name': full_group_name,
                        'label': sys.label,
                        'systems': group_systems,
                        'depth': depth,
                        'is_expanded': True  # Groups that show up here are expanded
                    })

                    # Recursively collect nested groups
                    collect_groups(sys.subsystem, prefix=group_prefix, depth=depth + 1)

        collect_groups(self)
        return groups

    def is_group_expanded(self, group_name: str) -> bool:
        """
        Check if a group is currently expanded.

        Parameters
        ----------
        group_name : str
            The group name (can include dot notation for nested groups)

        Returns
        -------
        bool
            True if the group is expanded (subsystem is not None), False otherwise
        """
        def find_system(name, prefix=''):
            for sys in self.systems:
                full_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name
                if full_name == name:
                    return sys

                # Check nested groups
                if sys.subsystem is not None:
                    group_prefix = f"{full_name}."
                    result = find_in_subsystem(sys.subsystem, name, group_prefix)
                    if result:
                        return result
            return None

        def find_in_subsystem(xdsm_inst, full_name, prefix):
            for sys in xdsm_inst.systems:
                sys_full_name = f"{prefix}{sys.node_name}"
                if sys_full_name == full_name:
                    return sys

                if sys.subsystem is not None:
                    result = find_in_subsystem(sys.subsystem, full_name, f"{sys_full_name}.")
                    if result:
                        return result
            return None

        system = find_system(group_name)
        return system is not None and system.subsystem is not None

    def swap_systems(self, system1_name: str, system2_name: str) -> None:
        """
        Swap two systems, potentially across hierarchy boundaries.

        This method swaps the positions of two systems in the XDSM, even if one is in a
        nested group and the other is in the parent or a different group. All connections
        are updated to reflect the swap.

        Parameters
        ----------
        system1_name : str
            Name of the first system (can include dot notation for nested systems)
        system2_name : str
            Name of the second system (can include dot notation for nested systems)

        Examples
        --------
        >>> xdsm.swap_systems('d1', 'g1.d2')  # Swap top-level d1 with nested g1.d2
        """
        # Helper function to find a system and its parent XDSM
        def find_system(name, parent_xdsm=None, prefix=''):
            parts = name.split('.')

            # Check if it's a direct child of this XDSM
            for sys in self.systems:
                if prefix + sys.node_name == name:
                    return sys, self, sys.node_name

                # Check nested groups
                if sys.subsystem is not None:
                    group_prefix = f"{prefix}{sys.node_name}."
                    result = _find_in_subsystem(sys.subsystem, name, group_prefix)
                    if result:
                        return result

            return None

        def _find_in_subsystem(xdsm_inst, full_name, prefix):
            for sys in xdsm_inst.systems:
                if prefix + sys.node_name == full_name:
                    return sys, xdsm_inst, sys.node_name

                if sys.subsystem is not None:
                    group_prefix = f"{prefix}{sys.node_name}."
                    result = _find_in_subsystem(sys.subsystem, full_name, group_prefix)
                    if result:
                        return result
            return None

        # Find both systems
        sys1_info = find_system(system1_name)
        sys2_info = find_system(system2_name)

        if not sys1_info or not sys2_info:
            raise ValueError(f"Could not find systems: {system1_name}, {system2_name}")

        sys1, parent1, local_name1 = sys1_info
        sys2, parent2, local_name2 = sys2_info

        # Swap the systems in their respective parents
        idx1 = parent1.systems.index(sys1)
        idx2 = parent2.systems.index(sys2)

        if parent1 == parent2:
            # Same parent - simple swap
            parent1.systems[idx1], parent1.systems[idx2] = parent1.systems[idx2], parent1.systems[idx1]
        else:
            # Different parents - swap across boundaries
            parent1.systems[idx1] = sys2
            parent2.systems[idx2] = sys1

            # Update connections to reflect the swap
            self._update_connections_after_swap(system1_name, system2_name, local_name1, local_name2)

    def _update_connections_after_swap(self, full_name1, full_name2, local_name1, local_name2):
        """Update all connections after swapping two systems across hierarchy boundaries."""
        # Parse the full names to understand hierarchy
        parts1 = full_name1.split('.')
        parts2 = full_name2.split('.')

        # Update connections in the top-level XDSM
        for conn in self.connections:
            if conn.src == full_name1:
                conn.src = full_name2
            elif conn.src == full_name2:
                conn.src = full_name1

            if conn.target == full_name1:
                conn.target = full_name2
            elif conn.target == full_name2:
                conn.target = full_name1

        # Recursively update connections in nested groups
        self._update_nested_connections(full_name1, full_name2, local_name1, local_name2)

    def _update_nested_connections(self, full_name1, full_name2, local_name1, local_name2, prefix=''):
        """Recursively update connections within nested groups."""
        parts1 = full_name1.split('.')
        parts2 = full_name2.split('.')

        # Check each system to see if it's a group
        for sys in self.systems:
            if sys.subsystem is not None:
                group_prefix = f"{prefix}{sys.node_name}." if prefix else f"{sys.node_name}."

                # Check if either system belongs to this group
                sys1_in_group = full_name1.startswith(group_prefix)
                sys2_in_group = full_name2.startswith(group_prefix)

                # Update connections within this group's subsystem
                for conn in sys.subsystem.connections:
                    # Determine what names to use for updates
                    # If both systems are in this group, update using local names
                    if sys1_in_group and sys2_in_group:
                        # Both in same group - use local names (strip group prefix)
                        name1_in_group = full_name1[len(group_prefix):]
                        name2_in_group = full_name2[len(group_prefix):]

                        if conn.src == name1_in_group:
                            conn.src = name2_in_group
                        elif conn.src == name2_in_group:
                            conn.src = name1_in_group

                        if conn.target == name1_in_group:
                            conn.target = name2_in_group
                        elif conn.target == name2_in_group:
                            conn.target = name1_in_group

                # Recursively update deeper nested groups
                sys.subsystem._update_nested_connections(full_name1, full_name2, local_name1, local_name2, group_prefix)

    def add_system(self, node_name: str, style: Union[str, 'XDSM'],
                   label: Union[str, List[str], Tuple[str, ...]],
                   stack: bool = False, faded: bool = False, label_width: Optional[int] = None,
                   spec_name: Optional[str] = None) -> None:
        """
        Add a system block on the diagonal.

        Parameters
        ----------
        node_name : str
            Unique identifier for the system
        style : str or XDSM
            Either a style string (e.g., 'Function', 'Group') or an XDSM instance for nested groups
        label : str, list, or tuple
            Display label for the system
        stack : bool
            Display as stacked rectangles
        faded : bool
            Fade the component
        label_width : int, optional
            Number of items per line for multi-line labels
        spec_name : str, optional
            Name for spec file
        """
        # Check if style is an XDSM instance (nested group)
        if isinstance(style, XDSM):
            subsystem = style
            actual_style = 'Group'  # Default to Group style for nested XDSM
        else:
            subsystem = None
            actual_style = style

        system = SystemNode(
            node_name=node_name,
            style=actual_style,
            label=label,
            stack=stack,
            faded=faded,
            label_width=label_width,
            spec_name=spec_name,
            subsystem=subsystem
        )
        self.systems.append(system)
    
    def add_input(self, name: str, label: Union[str, List[str], Tuple[str, ...]],
                  label_width: Optional[int] = None, style: str = "DataIO",
                  stack: bool = False, faded: bool = False) -> None:
        """Add an input node at the top."""
        sys_faded = {s.node_name: s.faded for s in self.systems}
        
        if (self.auto_fade.inputs == "all") or \
           (self.auto_fade.inputs == "connected" and name in sys_faded and sys_faded[name]):
            faded = True
        
        self.inputs[name] = InputNode(
            node_name="output_" + name,
            label=label,
            label_width=label_width,
            style=style,
            stack=stack,
            faded=faded
        )
    
    def add_output(self, name: str, label: Union[str, List[str], Tuple[str, ...]],
                   label_width: Optional[int] = None, style: str = "DataIO",
                   stack: bool = False, faded: bool = False, side: str = "left") -> None:
        """Add an output node on the left or right side."""
        sys_faded = {s.node_name: s.faded for s in self.systems}
        
        if (self.auto_fade.outputs == "all") or \
           (self.auto_fade.outputs == "connected" and name in sys_faded and sys_faded[name]):
            faded = True
        
        output = OutputNode(
            node_name=f"{side}_output_{name}",
            label=label,
            label_width=label_width,
            style=style,
            stack=stack,
            faded=faded,
            side=side
        )
        
        self.outputs[name] = output
    
    def connect(self, src: str, target: str, label: Union[str, List[str], Tuple[str, ...]],
                label_width: Optional[int] = None, style: str = "DataInter",
                stack: bool = False, faded: bool = False) -> None:
        """
        Connect two components with a data line.

        Parameters
        ----------
        src : str
            Source system name (can include dot notation for nested systems)
        target : str
            Target system name (can include dot notation for nested systems)
        label : str, list, or tuple
            Connection label(s)
        label_width : int, optional
            Number of items per line for multi-line labels
        style : str
            Connection style
        stack : bool
            Display as stacked
        faded : bool
            Fade the connection

        Raises
        ------
        ValueError
            If source or target system does not exist in this XDSM
        """
        # Get all valid system names (including nested systems if they're referenced with dots)
        sys_faded = {s.node_name: s.faded for s in self.systems}

        # Check if source and target exist in this XDSM's systems
        # Note: dot notation (e.g., 'g1.d2') is allowed in parent XDSM to reference nested systems
        # but not allowed within the nested XDSM itself (it should use local names)
        src_parts = src.split('.')
        target_parts = target.split('.')

        # If there are dots in the name, it's referencing a nested system
        # This should only be valid if we're at the parent level
        if len(src_parts) > 1 or len(target_parts) > 1:
            # Dot notation is allowed at parent level - no validation needed here
            # The flattening process will handle the mapping
            pass
        else:
            # Local connection - validate that both systems exist
            if src not in sys_faded:
                import warnings
                warnings.warn(
                    f"Source system '{src}' not found in XDSM. "
                    f"Available systems: {list(sys_faded.keys())}",
                    UserWarning
                )
            if target not in sys_faded:
                import warnings
                warnings.warn(
                    f"Target system '{target}' not found in XDSM. "
                    f"Available systems: {list(sys_faded.keys())}",
                    UserWarning
                )

        src_faded = src in sys_faded and sys_faded[src]
        target_faded = target in sys_faded and sys_faded[target]

        all_faded = self.auto_fade.connections == "all"
        if (all_faded or
            (self.auto_fade.connections == "connected" and src_faded and target_faded) or
            (self.auto_fade.connections == "incoming" and target_faded) or
            (self.auto_fade.connections == "outgoing" and src_faded)):
            faded = True

        connection = ConnectionEdge(
            src=src,
            target=target,
            label=label,
            label_width=label_width,
            style=style,
            stack=stack,
            faded=faded,
            src_faded=src_faded,
            target_faded=target_faded
        )
        self.connections.append(connection)
    
    def add_process(self, systems: List[str], arrow: bool = True, faded: bool = False) -> None:
        """Add a process line between systems."""
        sys_faded = {s.node_name: s.faded for s in self.systems}

        if (self.auto_fade.processes == "all") or \
           (self.auto_fade.processes == "connected" and
            any([sys_faded.get(s, False) for s in systems])):
            faded = True

        process = ProcessChain(systems=systems, arrow=arrow, faded=faded)
        self.processes.append(process)

    def write(self, file_name: str, build: bool = True, cleanup: bool = True,
              quiet: bool = False, outdir: str = ".") -> None:
        """
        Write output files for the XDSM diagram (delegates to XDSMLatexWriter).

        Parameters
        ----------
        file_name : str
            Prefix for output files
        build : bool
            Whether to compile the PDF
        cleanup : bool
            Whether to delete build files after compilation
        quiet : bool
            Suppress pdflatex output
        outdir : str
            Output directory path
        """
        XDSMLatexWriter.write(self, file_name, build, cleanup, quiet, outdir)
    
    def to_latex(self, file_name: str, build: bool = True, cleanup: bool = True,
                 quiet: bool = False, outdir: str = ".") -> None:
        """
        Export XDSM diagram to LaTeX/TikZ format.
        
        Alias for write() method for clarity when exporting to LaTeX.

        Parameters
        ----------
        file_name : str
            Prefix for output files
        build : bool
            Whether to compile the PDF
        cleanup : bool
            Whether to delete build files after compilation
        quiet : bool
            Suppress pdflatex output
        outdir : str
            Output directory path
        """
        XDSMLatexWriter.write(self, file_name, build, cleanup, quiet, outdir)

    def write_html(self, file_name: str, title: str = "XDSM Diagram",
                   show_browser: bool = False) -> None:
        """
        Export XDSM diagram to HTML with TikZ rendered in browser using TikZJax.
        This produces output identical to the LaTeX/PDF version but viewable in a browser.
        
        Parameters
        ----------
        file_name : str
            Output HTML file name (with or without .html extension)
        title : str
            Title for the diagram
        show_browser : bool
            Whether to open the HTML file in browser after creation
        """
        from pyxdsm.xdsm_tikzjax_writer import XDSMTikZJaxWriter
        XDSMTikZJaxWriter.write(self, file_name, title, show_browser)
    

    def write_sys_specs(self, folder_name: str) -> None:
        """
        Write I/O spec JSON files for systems.

        Parameters
        ----------
        folder_name : str
            Folder to write spec files into
        """
        def _label_to_spec(label: Union[str, List[str], Tuple[str, ...]], spec: Set[str]) -> None:
            """Add label variables to spec set."""
            if isinstance(label, str):
                label = [label]
            for var in label:
                if var:
                    spec.add(var)

        specs = {}
        for sys in self.systems:
            specs[sys.node_name] = {"inputs": set(), "outputs": set()}
        
        # Add inputs from Input nodes
        for sys_name, inp in self.inputs.items():
            _label_to_spec(inp.label, specs[sys_name]["inputs"])
        
        # Add inputs/outputs from Connections
        for conn in self.connections:
            _label_to_spec(conn.label, specs[conn.target]["inputs"])
            _label_to_spec(conn.label, specs[conn.src]["outputs"])
        
        # Add outputs from Output nodes
        for sys_name, out in self.outputs.items():
            _label_to_spec(out.label, specs[sys_name]["outputs"])
        
        if not os.path.isdir(folder_name):
            os.mkdir(folder_name)
        
        for sys in self.systems:
            if sys.spec_name is not False and sys.spec_name is not None:
                path = os.path.join(folder_name, sys.spec_name + ".json")
                with open(path, "w") as f:
                    spec = specs[sys.node_name]
                    spec["inputs"] = list(spec["inputs"])
                    spec["outputs"] = list(spec["outputs"])
                    json_str = json.dumps(spec, indent=2)
                    f.write(json_str)
    
    def to_dict(self) -> dict:
        """Export XDSM specification to dictionary."""
        return self.model_dump()
    
    def to_json(self, filename: Optional[str] = None) -> str:
        """Export XDSM specification to JSON."""
        json_str = self.model_dump_json(indent=2)
        if filename:
            with open(filename, 'w') as f:
                f.write(json_str)
        return json_str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'XDSM':
        """Load XDSM from dictionary."""
        return cls.model_validate(data)
    
    @classmethod
    def from_json(cls, filename: str) -> 'XDSM':
        """Load XDSM from JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.model_validate(data)


# Example usage
if __name__ == "__main__":
    # Create XDSM with validation
    xdsm = XDSM(use_sfmath=True, auto_fade={'connections': 'connected'})
    
    # Add systems - note: use the proper style constants
    xdsm.add_system('opt', OPT, r'\text{Optimizer}')
    xdsm.add_system('d1', FUNC, r'\text{Discipline 1}')  # Changed to FUNC which is valid
    xdsm.add_system('d2', FUNC, r'\text{Discipline 2}')
    xdsm.add_system('func', FUNC, r'\text{Objective}')
    
    # Add connections
    xdsm.connect('opt', 'd1', r'x_1')
    xdsm.connect('opt', 'd2', r'x_2')
    xdsm.connect('d1', 'd2', r'y_1')
    xdsm.connect('d2', 'd1', r'y_2')
    xdsm.connect('d1', 'func', r'f_1')
    xdsm.connect('d2', 'func', r'f_2')
    xdsm.connect('func', 'opt', r'F')
    
    # Add process
    xdsm.add_process(['opt', 'd1', 'd2', 'func', 'opt'])
    
    # Export to JSON
    xdsm.to_json('xdsm_spec.json')
    
    # Write LaTeX files
    xdsm.write('example_xdsm', build=True)
    xdsm.write_html('example_xdsm')
    
    # Load from JSON
    xdsm_loaded = XDSM.from_json('xdsm_spec.json')
    print("Successfully loaded XDSM from JSON")
    
    # Validate example - this will raise an error
    try:
        bad_xdsm = XDSM()
        bad_xdsm.add_system('sys1', OPT, 'System 1')
        bad_xdsm.connect('sys1', 'sys1', 'Invalid')  # Self-connection error
    except ValueError as e:
        print(f"Validation caught error: {e}")
