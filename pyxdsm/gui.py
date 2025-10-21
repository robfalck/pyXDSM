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


def build_disciplines_from_xdsm(xdsm: XDSM) -> list:
    """
    Build a list of discipline elements from an XDSM object.

    This function flattens any nested XDSM groups and displays all
    leaf systems as if they are members of the top-level XDSM.

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram

    Returns
    -------
    list
        List of XDSMElement instances for the diagonal
    """
    # Get flattened systems (this recursively expands nested groups)
    flattened_systems = xdsm.get_flattened_systems()
    return [create_xdsm_element(sys) for sys in flattened_systems]


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
    # Get flattened systems and connections
    flattened_systems = xdsm.get_flattened_systems()
    flattened_connections = xdsm.get_flattened_connections()

    # Create a mapping from node_name to index in the flattened list
    node_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

    # Build the connection matrix
    connection_matrix = {}
    for conn in flattened_connections:
        src_idx = node_to_index.get(conn.src)
        tgt_idx = node_to_index.get(conn.target)

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
    # Get flattened systems and outputs
    flattened_systems = xdsm.get_flattened_systems()
    flattened_outputs = xdsm.get_flattened_outputs()

    # Create a mapping from node_name to index in the flattened list
    node_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

    # Build the output matrix - each row can have multiple outputs
    output_matrix = {}
    for sys_name, output_node in flattened_outputs.items():
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


def build_input_matrix(xdsm: XDSM) -> dict:
    """
    Build a matrix of inputs from the XDSM (top inputs).

    Parameters
    ----------
    xdsm : XDSM
        The XDSM diagram

    Returns
    -------
    dict
        Dictionary mapping column index to list of input labels
    """
    # Get flattened systems and inputs
    flattened_systems = xdsm.get_flattened_systems()
    flattened_inputs = xdsm.get_flattened_inputs()

    # Create a mapping from node_name to index in the flattened list
    node_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

    # Build the input matrix - each column can have multiple inputs
    input_matrix = {}
    for sys_name, input_node in flattened_inputs.items():
        sys_idx = node_to_index.get(sys_name)
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

    # Create toolbar with new callback
    MainToolbar(gui_instance=gui_instance, on_new_callback=refresh_diagram)

    # Scrollable container for the XDSM diagram
    scrollable_container = ui.element('div').classes('relative flex-1 overflow-auto')

    def build_xdsm_grid():
        """Build the XDSM grid from the current XDSM object."""
        # Create the connection canvas for drawing lines
        connection_canvas = dnd.ConnectionCanvas()

        # Build disciplines, connections, outputs, and inputs from the XDSM
        disciplines = build_disciplines_from_xdsm(gui_instance.xdsm)
        connections = build_connection_matrix(gui_instance.xdsm)
        outputs = build_output_matrix(gui_instance.xdsm)
        inputs = build_input_matrix(gui_instance.xdsm)

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
            canvas=connection_canvas,
            columns=num_cols
        ).classes('gap-x-1 gap-y-8 mt-8').style(f'min-width: {grid_width}px; width: {grid_width}px;')

        # Add group backgrounds to the canvas
        groups = gui_instance.xdsm.get_group_info()
        if groups:
            # Get flattened systems to map names to indices
            flattened_systems = gui_instance.xdsm.get_flattened_systems()
            sys_name_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

            # Register each group with the canvas
            for group_idx, group in enumerate(groups):
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

                    connection_canvas.add_group(
                        group_name=group['name'],
                        group_label=group_label,
                        system_ids=system_ids,
                        group_index=group_idx
                    )

        def on_reorder(reordered_disciplines):
            """Handle reordering of disciplines in the GUI."""
            # Update the XDSM object to match the new order
            gui_instance.sync_from_disciplines(reordered_disciplines)

            # Rebuild the connection, output, and input matrices based on the new system order
            new_connections = build_connection_matrix(gui_instance.xdsm)
            new_outputs = build_output_matrix(gui_instance.xdsm)
            new_inputs = build_input_matrix(gui_instance.xdsm)

            # Update the grid with the new connections, outputs, and inputs
            xdsm_grid.update_connections(new_connections, new_outputs, new_inputs)

            # Re-register group backgrounds after reordering
            groups = gui_instance.xdsm.get_group_info()
            if groups:
                # Get flattened systems to map names to indices
                flattened_systems = gui_instance.xdsm.get_flattened_systems()
                sys_name_to_index = {sys.node_name: i for i, sys in enumerate(flattened_systems)}

                # Register each group with the canvas
                for group_idx, group in enumerate(groups):
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

                        connection_canvas.add_group(
                            group_name=group['name'],
                            group_label=group_label,
                            system_ids=system_ids,
                            group_index=group_idx
                        )

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
