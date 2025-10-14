#!/usr/bin/env python3
from dataclasses import dataclass
import draganddrop as dnd
from nicegui import ui

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
    def __init__(self):
        super().__init__()
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


# Create arrow canvas in a relatively positioned container
with ui.element('div').classes('relative w-full h-screen'):
    # Create the arrow canvas
    # arrows = dnd.arrow_canvas()

    MainToolbar()


    disciplines = [dnd.Optimization(), dnd.Function(title='Analysis 1'),
                   dnd.Function(title='Analysis 2'), dnd.Function(title='Analysis 3')]
    n = len(disciplines)

    with dnd.DragGrid(columns=n).classes('gap-x-1 gap-y-8'):
        for i in range(n):
            for j in range(n):
                if i == j:
                    # Diagonal: discipline boxes
                    dnd.System(disciplines[i])
                elif j > i:
                    # Upper triangle: outputs
                    with ui.card().classes('w-40 h-40 flex items-center justify-center bg-blue-50'):
                        ui.icon('arrow_forward', size='sm')
                        ui.label(f'y{i}{j}').classes('text-xs')
                else:
                    # Lower triangle: inputs
                    with ui.card().classes('w-40 h-40 flex items-center justify-center bg-yellow-50'):
                        ui.icon('arrow_back', size='sm')
                        ui.label(f'x{j}{i}').classes('text-xs')


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
