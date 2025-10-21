from __future__ import annotations
from typing import Callable, Optional
from pydantic import BaseModel, Field
from nicegui import ui


class ConnectionCanvas(ui.html):
    """SVG canvas for drawing connection lines and group backgrounds between systems."""

    # Color palette for multiple groups
    GROUP_COLORS = [
        {'bg': 'rgba(200, 220, 240, 0.12)', 'border': 'rgba(100, 140, 180, 0.35)'},  # Blue
        {'bg': 'rgba(200, 240, 220, 0.12)', 'border': 'rgba(100, 180, 140, 0.35)'},  # Green
        {'bg': 'rgba(240, 220, 240, 0.12)', 'border': 'rgba(180, 140, 180, 0.35)'},  # Purple
        {'bg': 'rgba(240, 230, 200, 0.12)', 'border': 'rgba(180, 160, 100, 0.35)'},  # Gold
    ]

    def __init__(self) -> None:
        svg_content = '''
        <svg id="connection_canvas" class="absolute top-0 left-0 w-full h-full pointer-events-none" style="z-index: -1">
        </svg>
        '''
        super().__init__(content=svg_content, sanitize=False)
        self.connections = []
        self.groups = []

    def add_connection(self, source_id: str, target_id: str, data_id: str, is_feedback: bool):
        """
        Add a connection to be drawn.

        Args:
            source_id: ID of source system element
            target_id: ID of target system element
            data_id: ID of the DataInter element
            is_feedback: True if this is a feedback connection (backward), False if forward
        """
        self.connections.append({
            'type': 'inter',
            'source': source_id,
            'target': target_id,
            'data': data_id,
            'feedback': is_feedback
        })

    def add_input_connection(self, target_id: str, data_id: str):
        """
        Add an input connection (from top DataIO to system).

        Args:
            target_id: ID of target system element
            data_id: ID of the DataIO element
        """
        self.connections.append({
            'type': 'input',
            'target': target_id,
            'data': data_id
        })

    def add_output_connection(self, source_id: str, data_id: str):
        """
        Add an output connection (from system to right DataIO).

        Args:
            source_id: ID of source system element
            data_id: ID of the DataIO element
        """
        self.connections.append({
            'type': 'output',
            'source': source_id,
            'data': data_id
        })

    def add_group(self, group_name: str, group_label: str, system_ids: list, group_index: int = 0):
        """
        Add a group background for a set of systems.

        Args:
            group_name: Internal name of the group (e.g., 'g1')
            group_label: Display label for the group
            system_ids: List of system element IDs that belong to this group
            group_index: Index for color selection (0-3)
        """
        self.groups.append({
            'name': group_name,
            'label': group_label,
            'systems': system_ids,
            'color_index': group_index % len(self.GROUP_COLORS)
        })

    def draw_connections(self):
        """Draw all group backgrounds and connections on the canvas."""
        if not self.connections and not self.groups:
            return

        js_code = '''
        const svg = document.getElementById('connection_canvas');
        if (!svg) return;

        svg.innerHTML = ''; // Clear existing content

        const groups = %s;
        const connections = %s;
        const groupColors = %s;

        // STEP 1: Draw group backgrounds FIRST (so they appear behind everything)
        groups.forEach(group => {
            const systemElements = [];

            // Collect all system elements in this group
            group.systems.forEach(sysId => {
                const el = document.getElementById(sysId);
                if (el) systemElements.push(el);
            });

            if (systemElements.length === 0) return;

            // Calculate bounding box for all systems in the group
            const svgRect = svg.getBoundingClientRect();
            let minX = Infinity, minY = Infinity;
            let maxX = -Infinity, maxY = -Infinity;

            systemElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                const x1 = rect.left - svgRect.left;
                const y1 = rect.top - svgRect.top;
                const x2 = rect.right - svgRect.left;
                const y2 = rect.bottom - svgRect.top;

                minX = Math.min(minX, x1);
                minY = Math.min(minY, y1);
                maxX = Math.max(maxX, x2);
                maxY = Math.max(maxY, y2);
            });

            // Add padding around the group
            const padding = 24;
            minX -= padding;
            minY -= padding;
            maxX += padding;
            maxY += padding;

            // Get colors for this group
            const colors = groupColors[group.color_index];

            // Draw rounded rectangle background
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', minX);
            rect.setAttribute('y', minY);
            rect.setAttribute('width', maxX - minX);
            rect.setAttribute('height', maxY - minY);
            rect.setAttribute('rx', '12');  // Corner radius
            rect.setAttribute('ry', '12');
            rect.setAttribute('fill', colors.bg);
            rect.setAttribute('stroke', colors.border);
            rect.setAttribute('stroke-width', '2');
            rect.setAttribute('stroke-dasharray', '4 4');  // Dashed border
            rect.setAttribute('opacity', '1');

            svg.appendChild(rect);

            // Optional: Add group label in top-left corner
            // Uncomment if you want to show group labels
            /*
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', minX + 12);
            text.setAttribute('y', minY + 18);
            text.setAttribute('fill', colors.border);
            text.setAttribute('font-size', '10px');
            text.setAttribute('font-weight', '600');
            text.setAttribute('text-transform', 'uppercase');
            text.textContent = group.label;
            svg.appendChild(text);
            */
        });

        // STEP 2: Draw connections on top of group backgrounds

        connections.forEach(conn => {
            const dataEl = document.getElementById(conn.data);
            if (!dataEl) return;

            const dataRect = dataEl.getBoundingClientRect();
            const svgRect = svg.getBoundingClientRect();

            if (conn.type === 'input') {
                // Input connection: bottom of DataIO -> top of target system
                const targetEl = document.getElementById(conn.target);
                if (!targetEl) return;

                const targetRect = targetEl.getBoundingClientRect();

                const x1 = dataRect.left + dataRect.width / 2 - svgRect.left;
                const y1 = dataRect.bottom - svgRect.top;
                const x2 = targetRect.left + targetRect.width / 2 - svgRect.left;
                const y2 = targetRect.top - svgRect.top;

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d = `M ${x1} ${y1} L ${x2} ${y2}`;
                path.setAttribute('d', d);
                path.setAttribute('stroke', 'rgb(153, 153, 153)');
                path.setAttribute('stroke-width', '5');
                path.setAttribute('stroke-linecap', 'butt');
                path.setAttribute('fill', 'none');
                svg.appendChild(path);
            } else if (conn.type === 'output') {
                // Output connection: right of source system -> left of DataIO
                const sourceEl = document.getElementById(conn.source);
                if (!sourceEl) return;

                const sourceRect = sourceEl.getBoundingClientRect();

                const x1 = sourceRect.right - svgRect.left;
                const y1 = sourceRect.top + sourceRect.height / 2 - svgRect.top;
                const x2 = dataRect.left - svgRect.left;
                const y2 = dataRect.top + dataRect.height / 2 - svgRect.top;

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d = `M ${x1} ${y1} L ${x2} ${y1}`;
                path.setAttribute('d', d);
                path.setAttribute('stroke', 'rgb(153, 153, 153)');
                path.setAttribute('stroke-width', '5');
                path.setAttribute('stroke-linecap', 'butt');
                path.setAttribute('fill', 'none');
                svg.appendChild(path);
            } else {
                // Inter-system connection (existing logic)
                const sourceEl = document.getElementById(conn.source);
                const targetEl = document.getElementById(conn.target);

                if (!sourceEl || !targetEl) return;

                const sourceRect = sourceEl.getBoundingClientRect();
                const targetRect = targetEl.getBoundingClientRect();

            if (conn.feedback) {
                // Feedback connection: left of source -> horizontal -> right of data (hide diagonal) -> vertical -> top of data -> vertical -> bottom of target
                // Point 1: left side of source system
                const x1 = sourceRect.left - svgRect.left;
                const y1 = sourceRect.top + sourceRect.height / 2 - svgRect.top;

                // Point 2: right side of data element (for horizontal line)
                const x2 = dataRect.right - svgRect.left;
                const y2 = dataRect.top + dataRect.height / 2 - svgRect.top;

                // Point 3: top of data element (vertical line from top of data)
                const x3 = dataRect.left + dataRect.width / 2 - svgRect.left;
                const y3 = dataRect.top - svgRect.top;

                // Point 4: bottom of target system
                const x4 = targetRect.left + targetRect.width / 2 - svgRect.left;
                const y4 = targetRect.bottom - svgRect.top;

                // Draw first segment: horizontal from source to data (at y1)
                const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d1 = `M ${x1} ${y1} L ${x2} ${y1}`;
                path1.setAttribute('d', d1);
                path1.setAttribute('stroke', 'rgb(153, 153, 153)'); // black!40 as solid gray
                path1.setAttribute('stroke-width', '5');
                path1.setAttribute('stroke-linecap', 'butt');
                path1.setAttribute('fill', 'none');
                svg.appendChild(path1);

                // Draw second segment: vertical from top of data to target (at x3)
                const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d2 = `M ${x3} ${y3} L ${x4} ${y4}`;
                path2.setAttribute('d', d2);
                path2.setAttribute('stroke', 'rgb(153, 153, 153)'); // black!40 as solid gray
                path2.setAttribute('stroke-width', '5');
                path2.setAttribute('stroke-linecap', 'butt');
                path2.setAttribute('fill', 'none');
                svg.appendChild(path2);
            } else {
                // Forward connection: right of source -> horizontal -> left of data (hide diagonal) -> vertical -> bottom of data -> vertical -> top of target
                // Point 1: right side of source system
                const x1 = sourceRect.right - svgRect.left;
                const y1 = sourceRect.top + sourceRect.height / 2 - svgRect.top;

                // Point 2: left side of data element (for horizontal line)
                const x2 = dataRect.left - svgRect.left;
                const y2 = dataRect.top + dataRect.height / 2 - svgRect.top;

                // Point 3: bottom of data element (vertical line starts from bottom of data)
                const x3 = dataRect.left + dataRect.width / 2 - svgRect.left;
                const y3 = dataRect.bottom - svgRect.top;

                // Point 4: top of target system
                const x4 = targetRect.left + targetRect.width / 2 - svgRect.left;
                const y4 = targetRect.top - svgRect.top;

                // Draw first segment: horizontal from source to data (at y1)
                const path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d1 = `M ${x1} ${y1} L ${x2} ${y1}`;
                path1.setAttribute('d', d1);
                path1.setAttribute('stroke', 'rgb(153, 153, 153)'); // black!40 as solid gray
                path1.setAttribute('stroke-width', '5');
                path1.setAttribute('stroke-linecap', 'butt');
                path1.setAttribute('fill', 'none');
                svg.appendChild(path1);

                // Draw second segment: vertical from bottom of data to target (at x3)
                const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d2 = `M ${x3} ${y3} L ${x4} ${y4}`;
                path2.setAttribute('d', d2);
                path2.setAttribute('stroke', 'rgb(153, 153, 153)'); // black!40 as solid gray
                path2.setAttribute('stroke-width', '5');
                path2.setAttribute('stroke-linecap', 'butt');
                path2.setAttribute('fill', 'none');
                svg.appendChild(path2);
            }
            }
        });
        ''' % (
            str(self.groups).replace("'", '"').replace('True', 'true').replace('False', 'false'),
            str(self.connections).replace("'", '"').replace('True', 'true').replace('False', 'false'),
            str(self.GROUP_COLORS).replace("'", '"')
        )

        ui.run_javascript(js_code)


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


class DataInter(XDSMElement):
    """Data connection between components (internal)."""

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = ''
        if 'classes' not in data:
            data['classes'] = 'w-28 h-14 flex items-center justify-center self-center'
        if 'style' not in data:
            # Light gray fill with parallelogram skew to match TikZ trapezium
            # TikZ uses trapezium with left angle 75° and right angle 105°
            # CSS skewX creates a parallelogram effect
            # Use solid background to hide connection lines behind it
            data['style'] = 'background-color: rgb(230, 230, 230); transform: skewX(-15deg); border: 1px solid rgba(0, 0, 0, 0.3);'
        super().__init__(**data)


class DataIO(XDSMElement):
    """Data I/O connection (input/output)."""

    def __init__(self, **data):
        if 'title' not in data:
            data['title'] = ''
        if 'classes' not in data:
            data['classes'] = 'w-28 h-14 flex items-center justify-center self-center'
        if 'style' not in data:
            # White fill with parallelogram skew to match TikZ trapezium
            # TikZ uses trapezium with left angle 75° and right angle 105°
            data['style'] = 'background-color: white; transform: skewX(-15deg); border: 1px solid rgba(0, 0, 0, 0.3);'
        super().__init__(**data)


class Connection(ui.card):
    """Display card for connections between systems."""

    def __init__(self, xdsm_element: XDSMElement, connection_id: Optional[str] = None) -> None:
        super().__init__()
        self.xdsm_element = xdsm_element

        # Set unique ID for line connections if provided
        if connection_id:
            self.props(f'id="{connection_id}"')

        # Apply styling from XDSMElement
        if xdsm_element.classes:
            self.classes(xdsm_element.classes)

        # Apply inline styles from XDSMElement
        if xdsm_element.style:
            self.style(xdsm_element.style)

        # Add the label with counter-skew to keep text readable
        with self:
            # Use HTML to render LaTeX with KaTeX
            ui.html(f'<div class="text-center text-xs font-semibold katex-content" style="transform: skewX(15deg);">{xdsm_element.title}</div>', sanitize=False)


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
            # Use HTML to render LaTeX with KaTeX
            ui.html(f'<div class="text-center font-bold katex-content">{xdsm_element.title}</div>', sanitize=False)

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
                 connections: Optional[dict] = None, outputs: Optional[dict] = None,
                 inputs: Optional[dict] = None, canvas: Optional[ConnectionCanvas] = None, **kwargs) -> None:
        """
        Initialize the DragGrid.

        Args:
            disciplines: List of XDSMElement instances for the diagonal
            on_reorder: Optional callback when disciplines are reordered
            connections: Optional dictionary mapping (row, col) tuples to connection labels
            outputs: Optional dictionary mapping row index to list of output labels
            inputs: Optional dictionary mapping column index to list of input labels
            canvas: Optional ConnectionCanvas for drawing connection lines
            **kwargs: Additional arguments passed to ui.grid
        """
        super().__init__(**kwargs)
        self.disciplines = disciplines
        self.on_reorder_callback = on_reorder
        self.connections = connections if connections is not None else {}
        self.outputs = outputs if outputs is not None else {}
        self.inputs = inputs if inputs is not None else {}
        self.system_cards: list[System] = []
        self.connection_cards: dict[tuple[int, int], Connection] = {}  # Track connection cards by (row, col)
        self.input_cards: dict[int, Connection] = {}  # Track input cards by column index
        self.output_cards: dict[int, Connection] = {}  # Track output cards by row index
        self.canvas = canvas
        self.n = len(disciplines)

        # Check if we need an output column and/or input row
        self.has_outputs = len(self.outputs) > 0
        self.has_inputs = len(self.inputs) > 0

        # Set up drop zones on each diagonal cell
        self.render()

    def update_connections(self, connections: dict, outputs: Optional[dict] = None,
                          inputs: Optional[dict] = None):
        """
        Update the connection matrix and optionally outputs/inputs, then re-render the grid.

        Args:
            connections: New dictionary mapping (row, col) tuples to connection labels
            outputs: Optional dictionary mapping row index to list of output labels
            inputs: Optional dictionary mapping column index to list of input labels
        """
        self.connections = connections
        if outputs is not None:
            self.outputs = outputs
            self.has_outputs = len(self.outputs) > 0
        if inputs is not None:
            self.inputs = inputs
            self.has_inputs = len(self.inputs) > 0
        self.render()

    def render(self):
        """Render the XDSM grid with disciplines on diagonal and data off-diagonal."""
        # Clear existing content
        self.clear()
        self.system_cards.clear()
        self.connection_cards.clear()
        self.input_cards.clear()
        self.output_cards.clear()
        DragGrid.preview_systems.clear()

        # Clear canvas connections and groups if we have a canvas
        if self.canvas:
            self.canvas.connections.clear()
            self.canvas.groups.clear()

        # Determine grid dimensions
        # Rows: 1 input row (if needed) + n system rows
        # Cols: n systems + 1 output column (if needed)
        num_rows = (1 if self.has_inputs else 0) + self.n
        num_cols = self.n + (1 if self.has_outputs else 0)

        # Track which connections need to be registered with canvas (deferred until all systems are created)
        deferred_connections = []

        with self:
            for i in range(num_rows):
                for j in range(num_cols):
                    # Check if we're in the input row
                    if self.has_inputs and i == 0:
                        # Input row at the top
                        if j < self.n:
                            # Check if this column has inputs
                            inputs_for_col = self.inputs.get(j, [])
                            if inputs_for_col:
                                # Display inputs using DataIO style
                                input_label = ', '.join(inputs_for_col)
                                input_id = f'input_{j}'
                                with ui.element('div').classes('w-40 h-20 flex items-center justify-center'):
                                    input_card = Connection(DataIO(title=input_label), connection_id=input_id)
                                    self.input_cards[j] = input_card
                            else:
                                # No input for this column
                                ui.label('').classes('w-40 h-20')
                        else:
                            # Top-right corner (input row, output column) - empty
                            ui.label('').classes('w-40 h-20')
                    else:
                        # System rows (adjust row index if we have an input row)
                        sys_row = i - (1 if self.has_inputs else 0)

                        if j < self.n:
                            # Within the main n x n grid
                            if sys_row == j:
                                # Diagonal: discipline boxes
                                system = System(self.disciplines[sys_row])
                                self.system_cards.append(system)

                                # Add drop zone behavior to the system card
                                system.on('dragover.prevent', lambda e, idx=sys_row: self.handle_dragover(e, idx))
                                system.on('drop', lambda e, idx=sys_row: self.handle_drop(e, idx))

                            else:
                                # Off-diagonal: check for connections
                                conn_label = self.connections.get((sys_row, j))
                                if conn_label:
                                    # Connection exists - display it using DataInter style
                                    conn_id = f'conn_{sys_row}_{j}'
                                    with ui.element('div').classes('w-40 h-20 flex items-center justify-center'):
                                        conn_card = Connection(DataInter(title=conn_label), connection_id=conn_id)
                                        self.connection_cards[(sys_row, j)] = conn_card

                                    # Defer connection registration until all systems are created
                                    if self.canvas:
                                        is_feedback = sys_row > j
                                        deferred_connections.append((sys_row, j, conn_id, is_feedback))
                                else:
                                    # No connection - don't display anything (empty space)
                                    ui.label('').classes('w-40 h-20')
                        else:
                            # Output column (rightmost column)
                            outputs_for_row = self.outputs.get(sys_row, [])
                            if outputs_for_row:
                                # Display outputs using DataIO style
                                # For multiple outputs, show them comma-separated
                                output_label = ', '.join(outputs_for_row)
                                output_id = f'output_{sys_row}'
                                with ui.element('div').classes('w-40 h-20 flex items-center justify-center'):
                                    output_card = Connection(DataIO(title=output_label), connection_id=output_id)
                                    self.output_cards[sys_row] = output_card
                            else:
                                # No output for this row
                                ui.label('').classes('w-40 h-20')

        # Now that all system cards are created, register deferred connections with canvas
        if self.canvas and deferred_connections:
            for sys_row, col, conn_id, is_feedback in deferred_connections:
                source_id = f'card_{id(self.system_cards[sys_row])}'
                target_id = f'card_{id(self.system_cards[col])}'
                self.canvas.add_connection(source_id, target_id, conn_id, is_feedback)

        # Register input connections (from DataIO to systems)
        if self.canvas:
            for col_idx, input_card in self.input_cards.items():
                target_id = f'card_{id(self.system_cards[col_idx])}'
                input_id = f'input_{col_idx}'
                self.canvas.add_input_connection(target_id, input_id)

        # Register output connections (from systems to DataIO)
        if self.canvas:
            for row_idx, output_card in self.output_cards.items():
                source_id = f'card_{id(self.system_cards[row_idx])}'
                output_id = f'output_{row_idx}'
                self.canvas.add_output_connection(source_id, output_id)

        # Draw connections after rendering is complete
        if self.canvas:
            ui.timer(0.1, self.canvas.draw_connections, once=True)

        # Render all LaTeX expressions using KaTeX
        ui.timer(0.15, lambda: ui.run_javascript('''
            document.querySelectorAll('.katex-content').forEach(el => {
                if (window.renderMathInElement) {
                    renderMathInElement(el, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false}
                        ],
                        throwOnError: false
                    });
                }
            });
        '''), once=True)

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
