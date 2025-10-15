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


# Create a global GUI instance to hold the XDSM reference
gui_instance = XDSMGUI()

# Create arrow canvas in a relatively positioned container
with ui.element('div').classes('relative w-full h-screen'):
    # Create the arrow canvas
    # arrows = dnd.arrow_canvas()

    MainToolbar(gui_instance=gui_instance)

    disciplines = [dnd.Optimization(), dnd.Function(title='Analysis 1'),
                   dnd.Function(title='Analysis 2'), dnd.Function(title='Analysis 3')]

    def on_reorder(reordered_disciplines):
        ui.notify(f'Disciplines reordered: {[d.title for d in reordered_disciplines]}')

    dnd.DragGrid(
        disciplines=disciplines,
        on_reorder=on_reorder,
        columns=len(disciplines)
    ).classes('gap-x-1 gap-y-8')


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
