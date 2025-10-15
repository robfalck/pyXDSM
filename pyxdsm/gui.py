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


class MainToolbar(ui.row):
    def __init__(self, gui_instance):
        super().__init__()
        self.gui = gui_instance
        self.classes('bg-zinc-200')

        with self:
            ui.button('New', on_click=lambda: ui.notify('New Model Requested'))

            with ui.dropdown_button('Export', auto_close=True):
                ui.item('PDF', on_click=lambda: ui.notify('Exporting to PDF'))
                ui.item('JSON', on_click=lambda: ui.notify('Exporting to JSON'))

            self.lock_icon = ui.icon('lock_open', size='md')
            self.switch = ui.switch('Unlocked')
            self.switch.on_value_change(self._on_toggle)

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

    def sync_from_disciplines(self, disciplines: list):
        """
        Synchronize the XDSM systems list from the GUI disciplines list.

        This updates the XDSM to match the current order and state of
        the disciplines shown in the GUI.

        Parameters
        ----------
        disciplines : list
            List of XDSMElement instances from the GUI
        """
        # Map discipline titles back to system nodes
        # We need to find which system corresponds to each discipline
        new_order = []
        for discipline in disciplines:
            # Find the system with matching label
            for system in self.xdsm.systems:
                system_label = system.label
                if isinstance(system_label, (list, tuple)):
                    system_label = ', '.join(system_label)

                if system_label == discipline.title:
                    new_order.append(system)
                    break

        # Update the systems list
        if len(new_order) == len(self.xdsm.systems):
            self.xdsm.systems = new_order


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


def build_disciplines_from_xdsm(xdsm: XDSM) -> list:
    """
    Build a list of discipline elements from an XDSM object.

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram

    Returns
    -------
    list
        List of XDSMElement instances for the diagonal
    """
    return [create_xdsm_element(sys) for sys in xdsm.systems]


def build_connection_matrix(xdsm: XDSM) -> dict:
    """
    Build a matrix of connections from the XDSM.

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram

    Returns
    -------
    dict
        Dictionary mapping (row, col) tuples to connection labels
    """
    # Create a mapping from node_name to index
    node_to_index = {sys.node_name: i for i, sys in enumerate(xdsm.systems)}

    # Build the connection matrix
    connection_matrix = {}
    for conn in xdsm.connections:
        src_idx = node_to_index.get(conn.src)
        tgt_idx = node_to_index.get(conn.target)

        if src_idx is not None and tgt_idx is not None:
            # Get the label text
            if isinstance(conn.label, (list, tuple)):
                label_text = ', '.join(conn.label)
            else:
                label_text = conn.label

            # Store as (row, col) -> label
            # In XDSM, connection from src to target appears at position (src_row, target_col)
            # Forward connections (src < target) appear in upper triangle
            # Backward/feedback connections (src > target) appear in lower triangle
            connection_matrix[(src_idx, tgt_idx)] = label_text

    return connection_matrix


def build_output_matrix(xdsm: XDSM) -> dict:
    """
    Build a matrix of outputs from the XDSM (right side outputs).

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram

    Returns
    -------
    dict
        Dictionary mapping row index to list of output labels
    """
    # Create a mapping from node_name to index
    node_to_index = {sys.node_name: i for i, sys in enumerate(xdsm.systems)}

    # Build the output matrix - each row can have multiple outputs
    output_matrix = {}
    for sys_name, output_node in xdsm.outputs.items():
        # Only process right-side outputs
        if output_node.side == 'right':
            sys_idx = node_to_index.get(sys_name)
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


# Create a sample XDSM with 4 systems
sample_xdsm = XDSM()
sample_xdsm.add_system('opt', 'Optimization', r'Optimization')
sample_xdsm.add_system('d1', 'Function', r'Analysis 1')
sample_xdsm.add_system('d2', 'Function', r'Analysis 2')
sample_xdsm.add_system('d3', 'Function', r'Analysis 3')

# Add connections between systems
sample_xdsm.connect('d1', 'd2', r'y')  # Analysis 1 -> Analysis 2
sample_xdsm.connect('d2', 'd3', r'z')  # Analysis 2 -> Analysis 3
sample_xdsm.connect('d3', 'opt', r'f')  # Analysis 3 -> Optimization

# Add outputs for Analysis 1 (pass as list to include both)
sample_xdsm.add_output('d1', [r'a', r'b'], side='right')  # Analysis 1 outputs 'a' and 'b'

# Create a global GUI instance to hold the XDSM reference
gui_instance = XDSMGUI(xdsm=sample_xdsm)

# Create arrow canvas in a relatively positioned container
with ui.element('div').classes('relative w-full h-screen'):
    # Create the arrow canvas
    # arrows = dnd.arrow_canvas()

    MainToolbar(gui_instance=gui_instance)

    # Build disciplines, connections, and outputs from the XDSM
    disciplines = build_disciplines_from_xdsm(gui_instance.xdsm)
    connections = build_connection_matrix(gui_instance.xdsm)
    outputs = build_output_matrix(gui_instance.xdsm)

    # Calculate number of columns: systems + output column (if there are outputs)
    num_cols = len(disciplines) + (1 if outputs else 0)

    # Create the DragGrid and store reference
    xdsm_grid = dnd.DragGrid(
        disciplines=disciplines,
        on_reorder=None,  # Will set after defining the callback
        connections=connections,
        outputs=outputs,
        columns=num_cols
    ).classes('gap-x-1 gap-y-8')

    def on_reorder(reordered_disciplines):
        """Handle reordering of disciplines in the GUI."""
        # Update the XDSM object to match the new order
        gui_instance.sync_from_disciplines(reordered_disciplines)

        # Rebuild the connection and output matrices based on the new system order
        new_connections = build_connection_matrix(gui_instance.xdsm)
        new_outputs = build_output_matrix(gui_instance.xdsm)

        # Update the grid with the new connections and outputs
        xdsm_grid.update_connections(new_connections, new_outputs)

        # Show notification with the new order
        system_names = [sys.node_name for sys in gui_instance.xdsm.systems]
        ui.notify(f'XDSM systems reordered: {system_names}')

    # Set the callback after defining it
    xdsm_grid.on_reorder_callback = on_reorder


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
