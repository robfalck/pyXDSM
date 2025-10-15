from __future__ import annotations
from typing import Callable, Optional
from pydantic import BaseModel, Field
from nicegui import ui


# class arrow_canvas(ui.html):
#     """Canvas for drawing arrows between cards."""

#     def __init__(self) -> None:
#         # Initialize arrows list FIRST before calling super().__init__
#         self._arrows = []

#         # Create SVG with arrowhead marker
#         svg_content = '''
#         <svg id="arrow_svg" class="absolute top-0 left-0 w-full h-full pointer-events-none" style="z-index: 1">
#             <defs>
#                 <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
#                     <polygon points="0 0, 10 3, 0 6" fill="#64748b" />
#                 </marker>
#             </defs>
#         </svg>
#         '''
#         super().__init__(content=svg_content, sanitize=False)

#     def add_arrow(self, from_card: 'card', to_card: 'card', from_side: str = 'right', to_side: str = 'top'):
#         """Add an arrow from one card to another.

#         Args:
#             from_card: Source card
#             to_card: Destination card
#             from_side: Side of source card ('left', 'right', 'top', 'bottom')
#             to_side: Side of destination card ('left', 'right', 'top', 'bottom')
#         """
#         arrow_id = f'arrow_{id(from_card)}_{id(to_card)}'
#         self._arrows.append({
#             'id': arrow_id,
#             'from': from_card,
#             'to': to_card,
#             'from_side': from_side,
#             'to_side': to_side
#         })
#         # Schedule arrow update after UI is ready
#         ui.timer(0.1, self._update_arrows, once=True)

#     def update(self):
#         """Manually trigger arrow redrawing (e.g., after drag-and-drop)."""
#         if hasattr(self, '_arrows'):
#             self._update_arrows()

#     def _update_arrows(self):
#         """Redraw all arrows based on current card positions."""
#         if not hasattr(self, '_arrows') or not self._arrows:
#             return

#         # JavaScript to get card positions and draw arrows
#         js_code = '''
#         const svg = document.getElementById('arrow_svg');
#         if (!svg) return;

#         svg.innerHTML = ''; // Clear existing arrows

#         const arrows = %s;

#         arrows.forEach(arrow => {
#             const fromEl = document.getElementById(arrow.from);
#             const toEl = document.getElementById(arrow.to);

#             if (!fromEl || !toEl) return;

#             const fromRect = fromEl.getBoundingClientRect();
#             const toRect = toEl.getBoundingClientRect();
#             const svgRect = svg.getBoundingClientRect();

#             // Calculate connection points
#             let x1, y1, x2, y2;

#             // From side
#             if (arrow.from_side === 'right') {
#                 x1 = fromRect.right - svgRect.left;
#                 y1 = fromRect.top + fromRect.height / 2 - svgRect.top;
#             } else if (arrow.from_side === 'left') {
#                 x1 = fromRect.left - svgRect.left;
#                 y1 = fromRect.top + fromRect.height / 2 - svgRect.top;
#             } else if (arrow.from_side === 'top') {
#                 x1 = fromRect.left + fromRect.width / 2 - svgRect.left;
#                 y1 = fromRect.top - svgRect.top;
#             } else { // bottom
#                 x1 = fromRect.left + fromRect.width / 2 - svgRect.left;
#                 y1 = fromRect.bottom - svgRect.top;
#             }

#             // To side
#             if (arrow.to_side === 'top') {
#                 x2 = toRect.left + toRect.width / 2 - svgRect.left;
#                 y2 = toRect.top - svgRect.top;
#             } else if (arrow.to_side === 'bottom') {
#                 x2 = toRect.left + toRect.width / 2 - svgRect.left;
#                 y2 = toRect.bottom - svgRect.top;
#             } else if (arrow.to_side === 'left') {
#                 x2 = toRect.left - svgRect.left;
#                 y2 = toRect.top + toRect.height / 2 - svgRect.top;
#             } else { // right
#                 x2 = toRect.right - svgRect.left;
#                 y2 = toRect.top + toRect.height / 2 - svgRect.top;
#             }

#             // Draw line with right angle (XDSM style: horizontal then vertical)
#             const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
#             const d = `M ${x1} ${y1} L ${x2} ${y1} L ${x2} ${y2}`;
#             path.setAttribute('d', d);
#             path.setAttribute('stroke', '#64748b');
#             path.setAttribute('stroke-width', '3');
#             path.setAttribute('fill', 'none');
#             path.setAttribute('marker-end', 'url(#arrowhead)');

#             svg.appendChild(path);
#         });
#         ''' % str([{
#             'id': a['id'],
#             'from': f'card_{id(a["from"])}',
#             'to': f'card_{id(a["to"])}',
#             'from_side': a['from_side'],
#             'to_side': a['to_side']
#         } for a in self._arrows]).replace("'", '"')

#         ui.run_javascript(js_code)


class XDSMElement(BaseModel):

    title : str = Field(..., description='Title of the element in the diagram.')
    classes : Optional[str] = Field(default=None, description="Tailwind CSS classes for the element")
    style : Optional[str] = Field(default=None, description="CSS Style for the element")

    def __init__(self, **data):
        super().__init__(**data)


class Optimization(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'Optimization'
        if 'classes' not in data:
            data['classes'] = 'w-40 h-20 flex items-center justify-center rounded-full self-center'
        if 'style' not in data:
            data['style'] = 'background-color: rgba(160, 203, 232, 0.8);'  # #A0CBE8 at 80% opacity
        super().__init__(**data)


class MDA(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'MDA'
        if 'classes' not in data:
            data['classes'] = 'w-40 h-20 flex items-center justify-center rounded-full self-center'
        if 'style' not in data:
            data['style'] = 'background-color: rgba(255, 190, 125, 0.8);'  # #FFBE7D at 80% opacity
        super().__init__(**data)


class DOE(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'DOE'
        if 'classes' not in data:
            data['classes'] = 'w-40 h-20 flex items-center justify-center rounded-full self-center'
        if 'style' not in data:
            data['style'] = 'background-color: rgba(160, 203, 232, 0.8);'  # #A0CBE8 at 80% opacity (same as Optimization)
        super().__init__(**data)


class SubOptimization(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'SubOptimization'
        if 'classes' not in data:
            # Chamfered rectangle - using clip-path for octagon shape
            data['classes'] = 'w-40 h-20 flex items-center justify-center self-center'
        if 'style' not in data:
            # Red color at 80% opacity + chamfered corners
            data['style'] = 'background-color: rgba(160, 203, 232, 0.8); clip-path: polygon(10% 0%, 90% 0%, 100% 50%, 90% 100%, 10% 100%, 0% 50%);'
        super().__init__(**data)


class Group(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'Group'
        if 'classes' not in data:
            # Chamfered rectangle - using clip-path for octagon shape
            data['classes'] = 'w-40 h-20 flex items-center justify-center self-center'
        if 'style' not in data:
            # Green color at 80% opacity + chamfered corners
            data['style'] = 'background-color: rgba(140, 209, 125, 0.8); clip-path: polygon(10% 0%, 90% 0%, 100% 50%, 90% 100%, 10% 100%, 0% 50%);'
        super().__init__(**data)


class ImplicitGroup(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'ImplicitGroup'
        if 'classes' not in data:
            # Chamfered rectangle - using clip-path for octagon shape
            data['classes'] = 'w-40 h-20 flex items-center justify-center self-center'
        if 'style' not in data:
            # Salmon color at 80% opacity + chamfered corners
            data['style'] = 'background-color: rgba(255, 157, 154, 0.8); clip-path: polygon(10% 0%, 90% 0%, 100% 50%, 90% 100%, 10% 100%, 0% 50%);'
        super().__init__(**data)


class Function(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'Function'
        if 'classes' not in data:
            data['classes'] = 'w-40 h-20 flex items-center justify-center rounded-sm self-center'
        if 'style' not in data:
            # Green color at 80% opacity
            data['style'] = 'background-color: rgba(140, 209, 125, 0.8);'
        super().__init__(**data)


class ImplicitFunction(XDSMElement):

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = 'ImplicitFunction'
        if 'classes' not in data:
            data['classes'] = 'w-40 h-20 flex items-center justify-center rounded-sm self-center'
        if 'style' not in data:
            # Salmon color at 80% opacity
            data['style'] = 'background-color: rgba(255, 157, 154, 0.8);'
        super().__init__(**data)


class System(ui.card):

    dragged: Optional['System'] = None

    def __init__(self, xdsm_element: XDSMElement) -> None:
        super().__init__()
        self.xdsm_element = xdsm_element

        # Set unique ID for arrow connections
        self.props(f'id="card_{id(self)}"')

        # Apply styling from XDSMElement
        if xdsm_element.classes:
            self.classes(xdsm_element.classes)

        # Add cursor pointer for draggability
        self.classes('cursor-pointer')

        # Apply inline styles from XDSMElement
        if xdsm_element.style:
            self.style(xdsm_element.style)

        with self:
            ui.label(xdsm_element.title).classes('text-center')

        # Make card draggable
        self.props('draggable')
        self.on('dragstart', self.handle_dragstart)
        self.on('dragend', self.handle_dragend)

    def handle_dragstart(self, _):
        System.dragged = self
        self.classes(add='opacity-50')

    def handle_dragend(self, _):
        self.classes(remove='opacity-50')


class DragGrid(ui.grid):
    """XDSM grid that supports drag-and-drop reordering of diagonal systems."""

    highlighted_index: Optional[int] = None
    preview_systems: list[Optional['System']] = []

    def __init__(self, disciplines: list[XDSMElement], on_reorder: Optional[Callable] = None,
                 connections: Optional[dict] = None, **kwargs) -> None:
        """
        Initialize the DragGrid.

        Args:
            disciplines: List of XDSMElement instances for the diagonal
            on_reorder: Optional callback when disciplines are reordered
            connections: Optional dictionary mapping (row, col) tuples to connection labels
            **kwargs: Additional arguments passed to ui.grid
        """
        super().__init__(**kwargs)
        self.disciplines = disciplines
        self.on_reorder_callback = on_reorder
        self.connections = connections if connections is not None else {}
        self.system_cards: list[System] = []
        self.n = len(disciplines)

        # Set up drop zones on each diagonal cell
        self.render()

    def update_connections(self, connections: dict):
        """
        Update the connection matrix and re-render the grid.

        Args:
            connections: New dictionary mapping (row, col) tuples to connection labels
        """
        self.connections = connections
        self.render()

    def render(self):
        """Render the XDSM grid with disciplines on diagonal and data off-diagonal."""
        # Clear existing content
        self.clear()
        self.system_cards.clear()
        DragGrid.preview_systems.clear()

        with self:
            for i in range(self.n):
                for j in range(self.n):
                    if i == j:
                        # Diagonal: discipline boxes
                        system = System(self.disciplines[i])
                        self.system_cards.append(system)

                        # Add drop zone behavior to the system card
                        system.on('dragover.prevent', lambda e, idx=i: self.handle_dragover(e, idx))
                        system.on('drop', lambda e, idx=i: self.handle_drop(e, idx))

                    else:
                        # Off-diagonal: check for connections
                        conn_label = self.connections.get((i, j))
                        if conn_label:
                            # Connection exists - display it
                            with ui.card().classes('w-40 h-40 flex items-center justify-center bg-green-50'):
                                ui.label(conn_label).classes('text-sm font-semibold')
                        else:
                            # No connection - don't display anything (empty space)
                            ui.label('').classes('w-40 h-40')

    def handle_dragover(self, _, target_index: int):
        """Handle dragover event on a diagonal system card."""
        if not System.dragged:
            return

        # Find the source index
        source_index = None
        for idx, card in enumerate(self.system_cards):
            if card == System.dragged:
                source_index = idx
                break

        if source_index is None or source_index == target_index:
            return

        # Show preview of reordering
        if DragGrid.highlighted_index != target_index:
            DragGrid.highlighted_index = target_index
            self._show_preview(target_index)

    def handle_drop(self, _, target_index: int):
        """Handle drop event - reorder the disciplines."""
        if not System.dragged:
            return

        # Find the source index
        source_index = None
        for idx, card in enumerate(self.system_cards):
            if card == System.dragged:
                source_index = idx
                break

        if source_index is None or source_index == target_index:
            self._clear_preview()
            return

        # Reorder disciplines
        discipline = self.disciplines.pop(source_index)
        self.disciplines.insert(target_index, discipline)

        # Clear preview and re-render
        self._clear_preview()
        DragGrid.highlighted_index = None
        self.render()

        # Call callback if provided
        if self.on_reorder_callback:
            self.on_reorder_callback(self.disciplines)

    def _show_preview(self, target_index: int):
        """Show semi-transparent preview of where systems will move."""
        # Clear existing previews
        self._clear_preview()

        # Add semi-transparent overlay to target position
        self.system_cards[target_index].classes(add='ring-4 ring-blue-400')

    def _clear_preview(self):
        """Clear all preview highlights."""
        for card in self.system_cards:
            card.classes(remove='ring-4 ring-blue-400')


# class column(ui.column):
#     highlighted: Optional[column] = None

#     def __init__(self, title: str, *, on_drop: Optional[Callable] = None) -> None:
#         super().__init__()
#         self.title = title
#         self.on_drop_callback = on_drop
#         self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2')

#         ui.label(title).classes('text-bold text-grey-8')
        
#         # Set up drop zone
#         self.on('dragover.prevent', self.handle_dragover)
#         self.on('dragleave', self.handle_dragleave)
#         self.on('drop', self.handle_drop)
    
#     def handle_dragover(self, _):
#         if column.highlighted != self:
#             if column.highlighted:
#                 column.highlighted.classes(remove='bg-blue-grey-3')
#             self.classes(add='bg-blue-grey-3')
#             column.highlighted = self
    
#     def handle_dragleave(self, _):
#         pass  # Keep highlight until drop or dragend
    
#     def handle_drop(self, _):
#         if card.dragged and card.dragged.parent_slot != self.default_slot:
#             # Move card to new column
#             card.dragged.move(self)

#             # Call the drop callback
#             if self.on_drop_callback:
#                 # Get column name from the stored title
#                 col_name = self.title
#                 self.on_drop_callback(card.dragged.item, col_name)

#         # Remove highlight
#         if column.highlighted:
#             column.highlighted.classes(remove='bg-blue-grey-3')
#             column.highlighted = None
