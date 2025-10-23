#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Optional
import pyxdsm.draganddrop as dnd
from nicegui import ui
from pyxdsm.XDSM import XDSM

ui.add_head_html('''
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body);"></script>
''')


@dataclass
class ToDo:
    title: str


def handle_drop(todo: ToDo, location: str):
    ui.notify(f'"{todo.title}" is now in {location}')


class SelectionToolbar(ui.row):
    """Toolbar that shows the selected system or connection and allows editing its name."""

    def __init__(self, gui_instance, on_name_change_callback=None, on_toggle_group_callback=None):
        super().__init__()
        self.gui = gui_instance
        self.on_name_change_callback = on_name_change_callback
        self.on_toggle_group_callback = on_toggle_group_callback
        self.selection_type = None
        self.selection_id = None
        self.classes('bg-zinc-100 items-center gap-4 p-2')

        with self:
            self.type_label = ui.label('No selection').classes('font-bold')
            self.name_input = ui.input(label='Name', placeholder='Select a system or connection',
                                      on_change=self._on_name_change)
            self.name_input.classes('w-96')
            self.name_input.disable()

            # Expand/Collapse button for groups (hidden by default)
            self.toggle_button = ui.button('Collapse Group', on_click=self._on_toggle_group)
            self.toggle_button.classes('ml-4')
            self.toggle_button.set_visibility(False)

    def set_selection(self, selection_type: str, selection_id, current_name: str, is_expanded: bool = False):
        """Update the toolbar with the selected element."""
        self.selection_type = selection_type
        self.selection_id = selection_id

        if selection_type == 'system':
            self.type_label.set_text(f'Selected System: {selection_id}')
            self.toggle_button.set_visibility(False)
        elif selection_type == 'connection':
            row, col = selection_id
            self.type_label.set_text(f'Selected Connection: ({row} → {col})')
            self.toggle_button.set_visibility(False)
        elif selection_type == 'group':
            self.type_label.set_text(f'Selected Group: {selection_id}')
            self.toggle_button.set_visibility(True)
            # Update button text based on current state
            if is_expanded:
                self.toggle_button.set_text('Collapse Group')
            else:
                self.toggle_button.set_text('Expand Group')

        self.name_input.enable()
        self.name_input.value = current_name

    def clear_selection(self):
        """Clear the selection."""
        self.selection_type = None
        self.selection_id = None
        self.type_label.set_text('No selection')
        self.name_input.value = ''
        self.name_input.disable()
        self.toggle_button.set_visibility(False)

    def _on_name_change(self, e):
        """Handle name input changes."""
        if self.on_name_change_callback and self.selection_type and self.selection_id is not None:
            self.on_name_change_callback(self.selection_type, self.selection_id, e.value)

    def _on_toggle_group(self):
        """Handle expand/collapse group button click."""
        if self.on_toggle_group_callback and self.selection_type == 'group' and self.selection_id:
            self.on_toggle_group_callback(self.selection_id)


class MainToolbar(ui.row):
    def __init__(self, gui_instance, on_new_callback=None):
        super().__init__()
        self.gui = gui_instance
        self.on_new_callback = on_new_callback
        self.classes('bg-zinc-200')

        with self:
            ui.button('New', on_click=self._new_diagram)

            with ui.dropdown_button('Export', auto_close=True):
                ui.item('PDF', on_click=self._export_pdf)
                ui.item('JSON', on_click=self._export_json)

            self.lock_icon = ui.icon('lock_open', size='md')
            self.switch = ui.switch('Unlocked')
            self.switch.on_value_change(self._on_toggle)

    async def _new_diagram(self):
        """Create a new empty XDSM diagram with confirmation."""
        # Show confirmation dialog
        with ui.dialog() as dialog, ui.card():
            ui.label('Are you sure you want to create a new diagram?').classes('text-lg mb-4')
            ui.label('This will discard the current diagram.').classes('text-sm text-gray-600 mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=lambda: dialog.submit(False)).props('flat')
                ui.button('Create New', on_click=lambda: dialog.submit(True)).props('color=primary')

        result = await dialog

        if result:
            try:
                # Create a new empty XDSM object
                new_xdsm = XDSM()

                # Update the GUI's XDSM reference
                self.gui.xdsm = new_xdsm

                # Call the callback to refresh the diagram
                if self.on_new_callback:
                    await self.on_new_callback()

                ui.notify('New XDSM diagram created!')
            except Exception as e:
                ui.notify(f'Error creating new diagram: {str(e)}', type='negative')

    def _export_pdf(self):
        """Export the XDSM diagram to PDF."""
        try:
            import tempfile
            import os

            # Create a temporary directory for the output
            with tempfile.TemporaryDirectory() as tmpdir:
                file_name = 'xdsm_diagram'

                # Call XDSM.write() to generate the PDF in the temp directory
                # The outdir parameter specifies where to put the output files
                self.gui.xdsm.write(file_name, build=True, cleanup=True, quiet=True, outdir=tmpdir)

                # The PDF will be at tmpdir/xdsm_diagram.pdf
                pdf_path = os.path.join(tmpdir, file_name + '.pdf')

                if os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        pdf_data = f.read()

                    # Trigger download in the browser
                    ui.download(pdf_data, 'xdsm_diagram.pdf')
                    ui.notify('PDF exported successfully!')
                else:
                    ui.notify(f'Error: PDF file not generated at {pdf_path}', type='negative')
        except Exception as e:
            ui.notify(f'Error exporting PDF: {str(e)}', type='negative')

    def _export_json(self):
        """Export the XDSM diagram to JSON."""
        try:
            # Convert XDSM to JSON string
            json_str = self.gui.xdsm.to_json()

            # Trigger download in the browser
            ui.download(json_str.encode('utf-8'), 'xdsm_diagram.json')
            ui.notify('JSON exported successfully!')
        except Exception as e:
            ui.notify(f'Error exporting JSON: {str(e)}', type='negative')

    def _on_toggle(self, e):
        ui.notify(e.value)
        if e.value:
            self.lock_icon.props('name=lock')
            self.switch.text = 'Locked'
        else:
            self.lock_icon.props('name=lock_open')
            self.switch.text = 'Unlocked'


class XDSMGUI:
    """
    GUI for visualizing and editing XDSM diagrams.

    Attributes
    ----------
    xdsm : XDSM
        Reference to the XDSM diagram being displayed/edited
    collapsed_groups : set
        Set of group names that should be displayed collapsed
    """

    def __init__(self, xdsm: Optional[XDSM] = None):
        """
        Initialize the XDSM GUI.

        Parameters
        ----------
        xdsm : XDSM, optional
            The XDSM diagram to display and edit. If None, starts with an empty diagram.
        """
        self.xdsm = xdsm if xdsm is not None else XDSM()
        self.collapsed_groups = set()  # Track which groups are collapsed

    def set_xdsm(self, xdsm: XDSM):
        """
        Set a new XDSM diagram to display.

        Parameters
        ----------
        xdsm : XDSM
            The XDSM diagram to display
        """
        self.xdsm = xdsm
        # TODO: Refresh the UI to display the new XDSM

    def get_xdsm(self) -> XDSM:
        """
        Get the current XDSM diagram.

        Returns
        -------
        XDSM
            The current XDSM diagram
        """
        return self.xdsm

    def reorder_systems(self, source_index: int, target_index: int):
        """
        Reorder systems in the XDSM when they are dragged in the GUI.

        Parameters
        ----------
        source_index : int
            The original index of the system being moved
        target_index : int
            The new index where the system should be placed
        """
        if source_index < 0 or source_index >= len(self.xdsm.systems):
            return
        if target_index < 0 or target_index >= len(self.xdsm.systems):
            return
        if source_index == target_index:
            return

        # Reorder the systems list
        system = self.xdsm.systems.pop(source_index)
        self.xdsm.systems.insert(target_index, system)

    def toggle_group_expansion(self, group_name: str):
        """
        Toggle whether a group is shown expanded or collapsed.

        Parameters
        ----------
        group_name : str
            The name of the group to toggle
        """
        if group_name in self.collapsed_groups:
            self.collapsed_groups.remove(group_name)
        else:
            self.collapsed_groups.add(group_name)

    def is_group_collapsed(self, group_name: str) -> bool:
        """
        Check if a group is currently collapsed.

        Parameters
        ----------
        group_name : str
            The name of the group to check

        Returns
        -------
        bool
            True if the group is collapsed, False if expanded
        """
        return group_name in self.collapsed_groups

    def sync_from_disciplines(self, disciplines: list):
        """
        Synchronize the XDSM systems list from the GUI disciplines list.

        This updates the XDSM to match the current order and state of
        the disciplines shown in the GUI, including swapping systems across
        hierarchy boundaries when necessary.

        Parameters
        ----------
        disciplines : list
            List of XDSMElement instances from the GUI
        """
        # Get the current flattened system list with their full names
        old_flattened = self.xdsm.get_flattened_systems()

        # Map discipline titles to system names (with dot notation)
        old_order = []
        for sys in old_flattened:
            sys_label = sys.label
            if isinstance(sys_label, (list, tuple)):
                sys_label = ', '.join(sys_label)
            old_order.append((sys.node_name, sys_label))

        # Map the new order from disciplines
        new_order = []
        for discipline in disciplines:
            # Find which system this discipline corresponds to
            for sys_name, sys_label in old_order:
                if sys_label == discipline.title:
                    new_order.append(sys_name)
                    break

        # Now detect swaps by comparing old and new orders
        if len(new_order) != len(old_order):
            return  # Something went wrong, bail out

        # Find pairs of systems that need to be swapped
        # We iterate through and find the first mismatch, swap it, and continue
        processed = set()
        for i in range(len(new_order)):
            if i in processed:
                continue

            old_name = old_order[i][0]
            new_name = new_order[i]

            if old_name != new_name:
                # Find where old_name is in the new order
                try:
                    j = new_order.index(old_name, i)
                    # Swap systems at positions i and j in the XDSM
                    self.xdsm.swap_systems(new_order[i], old_name)

                    # Update our tracking
                    new_order[i], new_order[j] = new_order[j], new_order[i]
                    processed.add(i)
                    processed.add(j)
                except ValueError:
                    # old_name not found in remaining list, skip
                    pass


# Mapping from XDSM system styles to draganddrop element classes
STYLE_MAP = {
    'Optimization': dnd.Optimization,
    'SubOptimization': dnd.SubOptimization,
    'MDA': dnd.MDA,
    'DOE': dnd.DOE,
    'ImplicitFunction': dnd.ImplicitFunction,
    'Function': dnd.Function,
    'Group': dnd.Group,
    'ImplicitGroup': dnd.ImplicitGroup,
}


def create_xdsm_element(system_node) -> dnd.XDSMElement:
    """
    Create a draganddrop XDSMElement from an XDSM SystemNode.

    Parameters
    ----------
    system_node : SystemNode
        The system node from the XDSM diagram

    Returns
    -------
    XDSMElement
        The corresponding draganddrop element
    """
    style_class = STYLE_MAP.get(system_node.style, dnd.Function)

    # Get the label text
    if isinstance(system_node.label, (list, tuple)):
        title = ', '.join(system_node.label)
    else:
        title = system_node.label

    return style_class(title=title)


def build_disciplines_from_xdsm(xdsm: XDSM, collapsed_groups: set = None) -> list:
    """
    Build a list of discipline elements from an XDSM object.

    This function flattens nested XDSM groups, but respects collapsed_groups
    and shows them as single icons instead of expanding them.

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram
    collapsed_groups : set, optional
        Set of group names that should be shown collapsed

    Returns
    -------
    list
        List of XDSMElement instances for the diagonal
    """
    if collapsed_groups is None:
        collapsed_groups = set()

    disciplines = []

    def process_systems(xdsm_instance, prefix=''):
        for sys in xdsm_instance.systems:
            full_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name

            if sys.subsystem is not None:
                # This is a group
                if full_name in collapsed_groups:
                    # Show as collapsed - single group icon
                    disciplines.append(create_xdsm_element(sys))
                else:
                    # Show as expanded - flatten the subsystems
                    group_prefix = f"{full_name}."
                    process_systems(sys.subsystem, prefix=group_prefix)
            else:
                # Regular system
                disciplines.append(create_xdsm_element(sys))

    process_systems(xdsm)
    return disciplines


def build_connection_matrix(xdsm: XDSM, collapsed_groups: set = None) -> dict:
    """
    Build a matrix of connections from the XDSM.

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram
    collapsed_groups : set, optional
        Set of group names that are collapsed

    Returns
    -------
    dict
        Dictionary mapping (row, col) tuples to connection labels
    """
    if collapsed_groups is None:
        collapsed_groups = set()

    # Get disciplines as displayed (respecting collapsed groups)
    disciplines = build_disciplines_from_xdsm(xdsm, collapsed_groups)

    # Build a mapping from system node_name to displayed discipline index
    # For collapsed groups, all systems within map to the group's index
    node_to_display_index = {}

    def map_systems_to_indices(xdsm_instance, prefix='', current_idx=[0]):
        for sys in xdsm_instance.systems:
            full_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name

            if sys.subsystem is not None:
                # This is a group
                if full_name in collapsed_groups:
                    # Collapsed: map all subsystems to this group's index
                    group_idx = current_idx[0]
                    node_to_display_index[full_name] = group_idx

                    # Map all nested systems to this group's index too
                    for nested_sys in sys.subsystem.get_flattened_systems(prefix=f"{full_name}."):
                        node_to_display_index[nested_sys.node_name] = group_idx

                    current_idx[0] += 1
                else:
                    # Expanded: recurse into subsystems
                    group_prefix = f"{full_name}."
                    map_systems_to_indices(sys.subsystem, prefix=group_prefix, current_idx=current_idx)
            else:
                # Regular system
                node_to_display_index[full_name] = current_idx[0]
                current_idx[0] += 1

    map_systems_to_indices(xdsm)

    # Get all connections
    flattened_connections = xdsm.get_flattened_connections()

    # Build the connection matrix
    connection_matrix = {}
    for conn in flattened_connections:
        src_idx = node_to_display_index.get(conn.src)
        tgt_idx = node_to_display_index.get(conn.target)

        if src_idx is not None and tgt_idx is not None:
            # Get the label text
            if isinstance(conn.label, (list, tuple)):
                label_text = ', '.join(conn.label)
            else:
                label_text = conn.label

            # Wrap in $ for KaTeX rendering if it contains LaTeX commands
            if '\\' in label_text and not label_text.startswith('$'):
                label_text = f'${label_text}$'

            # Store as (row, col) -> label
            # If multiple connections map to the same cell (due to collapsed groups),
            # combine their labels
            key = (src_idx, tgt_idx)
            if key in connection_matrix:
                connection_matrix[key] = f"{connection_matrix[key]}, {label_text}"
            else:
                connection_matrix[key] = label_text

    return connection_matrix


def build_output_matrix(xdsm: XDSM, collapsed_groups: set = None) -> dict:
    """
    Build a matrix of outputs from the XDSM (right side outputs).

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram
    collapsed_groups : set, optional
        Set of group names that are collapsed

    Returns
    -------
    dict
        Dictionary mapping row index to list of output labels
    """
    if collapsed_groups is None:
        collapsed_groups = set()

    # Build node to display index mapping (same as in connection matrix)
    node_to_display_index = {}

    def map_systems_to_indices(xdsm_instance, prefix='', current_idx=[0]):
        for sys in xdsm_instance.systems:
            full_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name

            if sys.subsystem is not None:
                if full_name in collapsed_groups:
                    group_idx = current_idx[0]
                    node_to_display_index[full_name] = group_idx
                    for nested_sys in sys.subsystem.get_flattened_systems(prefix=f"{full_name}."):
                        node_to_display_index[nested_sys.node_name] = group_idx
                    current_idx[0] += 1
                else:
                    group_prefix = f"{full_name}."
                    map_systems_to_indices(sys.subsystem, prefix=group_prefix, current_idx=current_idx)
            else:
                node_to_display_index[full_name] = current_idx[0]
                current_idx[0] += 1

    map_systems_to_indices(xdsm)

    # Get flattened outputs
    flattened_outputs = xdsm.get_flattened_outputs()

    # Build the output matrix - each row can have multiple outputs
    output_matrix = {}
    for sys_name, output_node in flattened_outputs.items():
        # Only process right-side outputs
        if output_node.side == 'right':
            sys_idx = node_to_display_index.get(sys_name)
            if sys_idx is not None:
                # Get the label text
                if isinstance(output_node.label, (list, tuple)):
                    label_text = ', '.join(output_node.label)
                else:
                    label_text = output_node.label

                # Store outputs as row_idx -> list of labels
                if sys_idx not in output_matrix:
                    output_matrix[sys_idx] = []
                output_matrix[sys_idx].append(label_text)

    return output_matrix


def build_input_matrix(xdsm: XDSM, collapsed_groups: set = None) -> dict:
    """
    Build a matrix of inputs from the XDSM (top inputs).

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram
    collapsed_groups : set, optional
        Set of group names that are collapsed

    Returns
    -------
    dict
        Dictionary mapping column index to list of input labels
    """
    if collapsed_groups is None:
        collapsed_groups = set()

    # Build node to display index mapping (same as in connection matrix)
    node_to_display_index = {}

    def map_systems_to_indices(xdsm_instance, prefix='', current_idx=[0]):
        for sys in xdsm_instance.systems:
            full_name = f"{prefix}{sys.node_name}" if prefix else sys.node_name

            if sys.subsystem is not None:
                if full_name in collapsed_groups:
                    group_idx = current_idx[0]
                    node_to_display_index[full_name] = group_idx
                    for nested_sys in sys.subsystem.get_flattened_systems(prefix=f"{full_name}."):
                        node_to_display_index[nested_sys.node_name] = group_idx
                    current_idx[0] += 1
                else:
                    group_prefix = f"{full_name}."
                    map_systems_to_indices(sys.subsystem, prefix=group_prefix, current_idx=current_idx)
            else:
                node_to_display_index[full_name] = current_idx[0]
                current_idx[0] += 1

    map_systems_to_indices(xdsm)

    # Get flattened inputs
    flattened_inputs = xdsm.get_flattened_inputs()

    # Build the input matrix - each column can have multiple inputs
    input_matrix = {}
    for sys_name, input_node in flattened_inputs.items():
        sys_idx = node_to_display_index.get(sys_name)
        if sys_idx is not None:
            # Get the label text
            if isinstance(input_node.label, (list, tuple)):
                label_text = ', '.join(input_node.label)
            else:
                label_text = input_node.label

            # Store inputs as col_idx -> list of labels
            if sys_idx not in input_matrix:
                input_matrix[sys_idx] = []
            input_matrix[sys_idx].append(label_text)

    return input_matrix


# Create a sample XDSM with 5 systems
sample_xdsm = XDSM()
sample_xdsm.add_system('opt', 'Optimization', r'Optimization')
sample_xdsm.add_system('d1', 'Function', r'Analysis 1')

sample_group = XDSM()

sample_group.add_system('newton', 'MDA', r'Newton')
sample_group.add_system('d2', 'Function', r'Analysis 2')
sample_group.add_system('d3', 'Function', r'Analysis 3')

sample_xdsm.add_system('g1', sample_group, r'Group 1')

# Add connections between systems
sample_xdsm.connect('opt', 'd1', r'x')  # Optimization -> Analysis 1
# sample_xdsm.connect('opt', 'newton', r'x')  # Optimization -> Newton
sample_xdsm.connect('opt', 'g1.d2', r'x')  # Optimization -> Analysis 2
# sample_xdsm.connect('d1', 'newton', r'y')  # Analysis 1 -> Newton
sample_xdsm.connect('d1', 'g1.d2', r'y')  # Analysis 1 -> Analysis 2

sample_group.connect('newton', 'd2', r'\theta')  # Newton -> Analysis 2
sample_group.connect('newton', 'd3', r'\theta')  # Newton -> Analysis 3
sample_group.connect('d2', 'd3', r'z')  # Analysis 2 -> Analysis 3
sample_group.connect('d3', 'newton', r'\mathcal{R}(\theta)')  # Analysis 3 -> Newton (feedback)

# Feedback connection from nested system to parent - must be defined in parent XDSM
sample_xdsm.connect('g1.d3', 'opt', r'f')  # Analysis 3 -> Optimization (feedback)

# Add outputs for Analysis 1 (pass as list to include both)
sample_xdsm.add_output('d1', [r'a', r'b'], side='right')  # Analysis 1 outputs 'a' and 'b'

# Add inputs for Analysis 2 (unconnected inputs from outside)
sample_group.add_input('d2', [r'p', r'q'])  # Analysis 2 inputs 'p' and 'q'

# Create a global GUI instance to hold the XDSM reference
gui_instance = XDSMGUI(xdsm=sample_xdsm)

sample_xdsm.write('group_test')

# Create arrow canvas in a relatively positioned container
with ui.element('div').classes('w-full h-screen flex flex-col'):
    async def refresh_diagram():
        """Refresh the XDSM diagram display after creating new diagram."""
        # Clear the scrollable container and rebuild the grid
        scrollable_container.clear()
        with scrollable_container:
            build_xdsm_grid()
        # Trigger KaTeX rendering for the new content
        ui.run_javascript('''
            setTimeout(() => {
                if (window.renderMathInElement) {
                    renderMathInElement(document.body, {
                        delimiters: [
                            {left: "$$", right: "$$", display: true},
                            {left: "$", right: "$", display: false}
                        ]
                    });
                }
            }, 100);
        ''')

    def on_name_change(selection_type: str, selection_id, new_name: str):
        """Handle name change from the SelectionToolbar."""
        if selection_type == 'system':
            # Update system label in XDSM
            flattened_systems = gui_instance.xdsm.get_flattened_systems()
            if 0 <= selection_id < len(flattened_systems):
                system_node = flattened_systems[selection_id]
                system_node.label = new_name

                # Rebuild the diagram to reflect the changes
                scrollable_container.clear()
                with scrollable_container:
                    build_xdsm_grid()

                # Trigger KaTeX rendering for the new content
                ui.run_javascript('''
                    setTimeout(() => {
                        if (window.renderMathInElement) {
                            renderMathInElement(document.body, {
                                delimiters: [
                                    {left: "$$", right: "$$", display: true},
                                    {left: "$", right: "$", display: false}
                                ]
                            });
                        }
                    }, 100);
                ''')

        elif selection_type == 'connection':
            # Update connection label in XDSM
            row_idx, col_idx = selection_id
            flattened_systems = gui_instance.xdsm.get_flattened_systems()
            flattened_connections = gui_instance.xdsm.get_flattened_connections()

            # Find the connection matching the row and column indices
            if row_idx < len(flattened_systems) and col_idx < len(flattened_systems):
                src_node = flattened_systems[row_idx]
                tgt_node = flattened_systems[col_idx]

                for conn in flattened_connections:
                    if conn.src == src_node.node_name and conn.target == tgt_node.node_name:
                        conn.label = new_name

                        # Rebuild the diagram to reflect the changes
                        scrollable_container.clear()
                        with scrollable_container:
                            build_xdsm_grid()

                        # Trigger KaTeX rendering for the new content
                        ui.run_javascript('''
                            setTimeout(() => {
                                if (window.renderMathInElement) {
                                    renderMathInElement(document.body, {
                                        delimiters: [
                                            {left: "$$", right: "$$", display: true},
                                            {left: "$", right: "$", display: false}
                                        ]
                                    });
                                }
                            }, 100);
                        ''')
                        break

    # Create toolbar with new callback
    MainToolbar(gui_instance=gui_instance, on_new_callback=refresh_diagram)

    # Scrollable container for the XDSM diagram
    scrollable_container = ui.element('div').classes('relative flex-1 overflow-auto')

    # Container for callback state
    class CallbackState:
        connection_canvas = None

    def on_toggle_group(group_name: str):
        """Handle expand/collapse toggle for a group."""
        gui_instance.toggle_group_expansion(group_name)

        # Rebuild the diagram to reflect the change
        scrollable_container.clear()
        with scrollable_container:
            build_xdsm_grid()

        # Trigger KaTeX rendering for the new content
        ui.run_javascript('''
            setTimeout(() => {
                if (window.renderMathInElement) {
                    renderMathInElement(document.body, {
                        delimiters: [
                            {left: "$$", right: "$$", display: true},
                            {left: "$", right: "$", display: false}
                        ]
                    });
                }
            }, 100);
        ''')

    # Create selection toolbar with callbacks
    selection_toolbar = SelectionToolbar(gui_instance=gui_instance, on_name_change_callback=on_name_change,
                                        on_toggle_group_callback=on_toggle_group)

    def on_selection(selection_type: str, selection_id, current_name: str):
        """Handle selection of a system or connection."""
        # For groups, check if they're expanded
        is_expanded = False
        if selection_type == 'group':
            is_expanded = not gui_instance.is_group_collapsed(selection_id)
        selection_toolbar.set_selection(selection_type, selection_id, current_name, is_expanded)

    def on_group_click(event_data):
        """Handle group selection from ConnectionCanvas."""
        group_name = event_data['name']
        group_label = event_data['label']
        is_expanded = not gui_instance.is_group_collapsed(group_name)

        # Clear system/connection selection
        if dnd.System.selected:
            old_id = f'card_{id(dnd.System.selected)}'
            ui.run_javascript(f'''
                const el = document.getElementById('{old_id}');
                if (el) el.style.border = 'none';
            ''')
            dnd.System.selected = None
        if dnd.Connection.selected:
            conn_id = dnd.Connection.selected.connection_id if dnd.Connection.selected.connection_id else f'conn_{dnd.Connection.selected.row_idx}_{dnd.Connection.selected.col_idx}'
            ui.run_javascript(f'''
                const el = document.getElementById('{conn_id}');
                if (el) el.style.border = 'none';
            ''')
            dnd.Connection.selected = None

        # Update selection toolbar
        selection_toolbar.set_selection('group', group_name, group_label, is_expanded)

        # Highlight the group
        if CallbackState.connection_canvas:
            CallbackState.connection_canvas.highlight_group(group_name)

    def build_xdsm_grid():
        """Build the XDSM grid from the current XDSM object."""
        # Set selection callback for System and Connection classes
        dnd.System.on_select_callback = on_selection
        dnd.Connection.on_select_callback = on_selection

        # Create the connection canvas for drawing lines
        CallbackState.connection_canvas = dnd.ConnectionCanvas()

        # Build disciplines, connections, outputs, and inputs from the XDSM
        disciplines = build_disciplines_from_xdsm(gui_instance.xdsm, gui_instance.collapsed_groups)
        connections = build_connection_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)
        outputs = build_output_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)
        inputs = build_input_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)

        # Calculate number of columns: systems + output column (if there are outputs)
        num_cols = len(disciplines) + (1 if outputs else 0)

        # Calculate fixed grid width: each cell is w-40 (160px) + gap-x-1 (0.25rem = 4px)
        # Adding some padding for margins
        grid_width = num_cols * 164 + 32  # 160px + 4px gap per column, plus 32px padding

        # Create the DragGrid and store reference with fixed minimum width
        xdsm_grid = dnd.DragGrid(
            disciplines=disciplines,
            on_reorder=None,  # Will set after defining the callback
            connections=connections,
            outputs=outputs,
            inputs=inputs,
            canvas=CallbackState.connection_canvas,
            columns=num_cols
        ).classes('gap-x-1 gap-y-8 mt-8').style(f'min-width: {grid_width}px; width: {grid_width}px;')

        # Add group backgrounds to the canvas (only for expanded groups)
        groups = gui_instance.xdsm.get_group_info()
        if groups:
            # Get flattened systems to map names to indices
            flattened_systems = gui_instance.xdsm.get_flattened_systems()
            sys_name_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

            # Register each group with the canvas (but skip collapsed ones)
            for group_idx, group in enumerate(groups):
                # Skip collapsed groups - they're shown as single icons
                if group['name'] in gui_instance.collapsed_groups:
                    continue

                # Map system names to card IDs
                system_ids = []
                for sys_name in group['systems']:
                    sys_idx = sys_name_to_index.get(sys_name)
                    if sys_idx is not None and sys_idx < len(xdsm_grid.system_cards):
                        card_id = f'card_{id(xdsm_grid.system_cards[sys_idx])}'
                        system_ids.append(card_id)

                # Add group to canvas if it has systems
                if system_ids:
                    group_label = group['label']
                    if isinstance(group_label, (list, tuple)):
                        group_label = ', '.join(group_label)

                    CallbackState.connection_canvas.add_group(
                        group_name=group['name'],
                        group_label=group_label,
                        system_ids=system_ids,
                        group_index=group_idx
                    )

                    # Create clickable overlay for this group
                    def make_click_handler(gname, glabel):
                        def handler(name, label):
                            on_group_click({'name': name, 'label': label})
                        return handler

                    overlay = dnd.GroupOverlay(
                        group_name=group['name'],
                        group_label=group_label,
                        on_click=make_click_handler(group['name'], group_label)
                    )
                    CallbackState.connection_canvas.group_overlays.append(overlay)

        def on_reorder(reordered_disciplines):
            """Handle reordering of disciplines in the GUI."""
            # Update the XDSM object to match the new order
            gui_instance.sync_from_disciplines(reordered_disciplines)

            # Rebuild the connection, output, and input matrices based on the new system order
            new_connections = build_connection_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)
            new_outputs = build_output_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)
            new_inputs = build_input_matrix(gui_instance.xdsm, gui_instance.collapsed_groups)

            # Update the grid with the new connections, outputs, and inputs
            xdsm_grid.update_connections(new_connections, new_outputs, new_inputs)

            # Re-register group backgrounds after reordering (only for expanded groups)
            groups = gui_instance.xdsm.get_group_info()
            if groups:
                # Get flattened systems to map names to indices
                flattened_systems = gui_instance.xdsm.get_flattened_systems()
                sys_name_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

                # Clear old overlays
                CallbackState.connection_canvas.group_overlays.clear()

                # Register each group with the canvas (but skip collapsed ones)
                for group_idx, group in enumerate(groups):
                    # Skip collapsed groups - they're shown as single icons
                    if group['name'] in gui_instance.collapsed_groups:
                        continue

                    # Map system names to card IDs
                    system_ids = []
                    for sys_name in group['systems']:
                        sys_idx = sys_name_to_index.get(sys_name)
                        if sys_idx is not None and sys_idx < len(xdsm_grid.system_cards):
                            card_id = f'card_{id(xdsm_grid.system_cards[sys_idx])}'
                            system_ids.append(card_id)

                    # Add group to canvas if it has systems
                    if system_ids:
                        group_label = group['label']
                        if isinstance(group_label, (list, tuple)):
                            group_label = ', '.join(group_label)

                        CallbackState.connection_canvas.add_group(
                            group_name=group['name'],
                            group_label=group_label,
                            system_ids=system_ids,
                            group_index=group_idx
                        )

                        # Create clickable overlay for this group (in reorder)
                        def make_click_handler_reorder(gname, glabel):
                            def handler(name, label):
                                on_group_click({'name': name, 'label': label})
                            return handler

                        overlay = dnd.GroupOverlay(
                            group_name=group['name'],
                            group_label=group_label,
                            on_click=make_click_handler_reorder(group['name'], group_label)
                        )
                        CallbackState.connection_canvas.group_overlays.append(overlay)

                # Position overlays after groups are redrawn (only if there are any)
                if CallbackState.connection_canvas.group_overlays:
                    ui.timer(0.15, CallbackState.connection_canvas.position_overlays, once=True)

            # Show notification with the new order
            system_names = [sys.node_name for sys in gui_instance.xdsm.systems]
            ui.notify(f'XDSM systems reordered: {system_names}')

        # Set the callback after defining it
        xdsm_grid.on_reorder_callback = on_reorder

    # Build the initial grid
    with scrollable_container:
        build_xdsm_grid()


    # with ui.row():
    #     with dnd.column('Next', on_drop=handle_drop):
    #         card_simplify = dnd.card(ToDo('Simplify Layouting'))
    #         dnd.card(ToDo('Provide Deployment'))
    #     with dnd.column('Doing', on_drop=handle_drop):
    #         card_improve = dnd.card(ToDo('Improve Documentation'))
    #     with dnd.column('Done', on_drop=handle_drop):
    #         dnd.card(ToDo('Invent NiceGUI'))
    #         dnd.card(ToDo('Test in own Projects'))
    #         dnd.card(ToDo('Publish as Open Source'))
    #         dnd.card(ToDo('Release Native-Mode'))

    # systems = [(ToDo('Optimizer'), {'shape': 'pill'}),
    #            (ToDo('Newton'), {'shape': 'pill'}),
    #            (ToDo('f'), {'shape': 'rectangle'}),
    #            (ToDo('g'), {'shape': 'rectangle'})]

    # n = 4
    # card_idx = 0
    # with ui.grid(columns=n+2):
    #     for row_i in range(n+2):
    #         for col_j in range(n+2):
    #             if row_i - 2 == col_j:
    #                 item, kwargs = systems[row_i-2]
    #                 dnd.card(item, **kwargs)
    #             else:
    #                 ui.label('')

    # # Draw arrow from Simplify Layouting to Improve Documentation
    # # arrows.add_arrow(card_simplify, card_improve, from_side='right', to_side='left')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(native=False, show=False)
