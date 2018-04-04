from __future__ import print_function
import os
from six import iteritems, string_types
import numpy as np

tikzpicture_template = r"""
%%% Preamble Requirements %%%
% \usepackage{{geometry}}
% \usepackage{{amsfonts}}
% \usepackage{{amsmath}}
% \usepackage{{amssymb}}
% \usepackage{{tikz}}

% \usetikzlibrary{{arrows,chains,positioning,scopes,shapes.geometric,shapes.misc,shadows}}

%%% End Preamble Requirements %%%

\input{{ {diagram_styles_path} }}
\begin{{tikzpicture}}

\matrix[MatrixSetup]{{
{nodes}}};

% XDSM process chains
{process}

\begin{{pgfonlayer}}{{data}}
\path
{edges}
\end{{pgfonlayer}}

\end{{tikzpicture}}
"""

tex_template = r"""
\documentclass{{article}}
\usepackage{{geometry}}
\usepackage{{amsfonts}}
\usepackage{{amsmath}}
\usepackage{{amssymb}}
\usepackage{{tikz}}

% Define the set of tikz packages to be included in the architecture diagram document
\usetikzlibrary{{arrows,chains,positioning,scopes,shapes.geometric,shapes.misc,shadows}}


% Set the border around all of the architecture diagrams to be tight to the diagrams themselves
% (i.e. no longer need to tinker with page size parameters)
\usepackage[active,tightpage]{{preview}}
\PreviewEnvironment{{tikzpicture}}
\setlength{{\PreviewBorder}}{{5pt}}

\begin{{document}}

\input{{ {tikzpicture_path} }}

\end{{document}}
"""


class XDSM(object):
    def __init__(self):
        self.comps = []
        self.connections = []
        self.left_outs = {}
        self.right_outs = {}
        self.ins = {}
        self.processes = []
        self.process_arrows = []

    def add_system(self, node_name, style, label, stack=False, faded=False):
        self.comps.append([node_name, style, label, stack, faded])

    def add_input(self, name, label, style='DataIO', stack=False):
        if name in self.ins:
            self.ins[name][2].append(label)
        else:
            self.ins[name] = ['input_' + name, style, [label], stack]

    def add_output(self, name, label, style='DataIO', stack=False, side="left"):
        if side == "left":
            if name in self.left_outs:
                self.left_outs[name][2].append(label)
            else:
                self.left_outs[name] = ['left_output_' + name, style, [label], stack]
        elif side == "right":
            if name in self.right_outs:
                self.right_outs[name][2].append(label)
            else:
                self.right_outs[name] = ['right_output_' + name, style, [label], stack]

    def connect(self, src, target, label, style='DataInter', stack=False, faded=False):
        if src == target:
            raise ValueError('Can not connect component to itself')
        self.connections.append([src, target, style, label, stack, faded])

    def add_process(self, systems, arrow=True):
        self.processes.append(systems)
        self.process_arrows.append(arrow)

    def from_openmdao_group(self, group, var_map=None):
        """
        Initializes a new XDSM from the given OpenMDAO group.

        Parameters
        ----------
        group : openmdao.api.group
            The group from which the XDSM should be constructed.

        """

        # Reset all members
        self.comps = []
        self.connections = []
        self.left_outs = {}
        self.right_outs = {}
        self.ins = {}
        self.processes = []
        self.process_arrows = []

        subsystems_ordered = group._subsystems_allprocs
        input_srcs = group._conn_global_abs_in2out

        connections = {
            tgt: src for tgt, src in iteritems(input_srcs) if src is not None
        }

        src2tgts = {}
        units = {n: data.get('units', '')
                 for n, data in iteritems(group._var_allprocs_abs2meta)}

        noconn_srcs = sorted((n for n in group._var_abs_names['output']
                              if n not in src2tgts), reverse=True)

        inputs = group.list_inputs(out_stream=None)
        outputs = group.list_outputs(out_stream=None)

        opt = 'Optimization'
        solver = 'MDA'
        comp = 'Analysis'
        group = 'Metamodel'
        func = 'Function'

        unconnected_outputs = set([o[0] for o in outputs])
        unconnected_inputs = set([input[0] for input in inputs])

        var_map = {} if var_map is None else var_map

        for system in subsystems_ordered:
            self.add_system(system.name, comp, r'{0}'.format(system.name.replace('_', ' ')))

        for tgt, src in iteritems(connections):
            unconnected_outputs.remove(src)
            unconnected_inputs.remove(tgt)
            name = src.split('.')[-1]
            label = var_map.get(name, name)
            self.connect(src.split('.')[0], tgt.split('.')[0], label)

        for output in sorted(unconnected_outputs):
            block, name = output.split('.')
            label = var_map.get(name, name)
            self.add_output(block, label, side='right')

        for input in sorted(unconnected_inputs):
            block, name = input.split('.')
            label = var_map.get(name, name)
            self.add_input(block, label)

    def _build_node_grid(self):
        size = len(self.comps)

        comps_rows = np.arange(size)
        comps_cols = np.arange(size)

        if self.ins:
            size += 1
            # move all comps down one row
            comps_rows += 1

        if self.left_outs:
            size += 1
            # shift all comps to the right by one, to make room for inputs
            comps_cols += 1

        if self.right_outs:
            size += 1
            # don't need to shift anything in this case

        # build a map between comp node_names and row idx for ordering calculations
        row_idx_map = {}
        col_idx_map = {}

        node_str = r'\node [{style}] ({node_name}) {{{node_label}}};'

        grid = np.empty((size, size), dtype=object)
        grid[:] = ''

        # add all the components on the diagonal
        for i_row, j_col, comp in zip(comps_rows, comps_cols, self.comps):
            style = comp[1]
            if comp[3] == True:  # stacking
                style += ',stack'
            if comp[4] == True:  # stacking
                style += ',faded'

            node = node_str.format(style=style, node_name=comp[0], node_label=comp[2])
            grid[i_row, j_col] = node

            row_idx_map[comp[0]] = i_row
            col_idx_map[comp[0]] = j_col

        # add all the off diagonal nodes from components
        for src, target, style, label, stack, faded in self.connections:
            src_row = row_idx_map[src]
            target_col = col_idx_map[target]

            loc = (src_row, target_col)

            style = style
            if stack == True:  # stacking
                style += ',stack'
            if faded == True:
                style += ',faded'

            node_name = '{}-{}'.format(src, target)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=label)

            grid[loc] = node

        # add the nodes for left outputs
        for comp_name, out_data in self.left_outs.items():
            node_name, style, labels, stack = out_data
            if stack:
                style += ',stack'

            i_row = row_idx_map[comp_name]
            loc = (i_row, 0)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=r' \\ '.join(labels))

            grid[loc] = node

            # add the nodes for right outputs
        for comp_name, out_data in self.right_outs.items():
            node_name, style, labels, stack = out_data
            if stack:
                style += ',stack'

            i_row = row_idx_map[comp_name]
            loc = (i_row, -1)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=r' \\ '.join(labels))

            grid[loc] = node

        # add the inputs to the top of the grid
        for comp_name, in_data in self.ins.items():
            node_name, style, labels, stack = in_data
            if stack:
                style = ',stack'

            j_col = col_idx_map[comp_name]
            loc = (0, j_col)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=r' \\ '.join(labels))

            grid[loc] = node

        # mash the grid data into a string
        rows_str = ''
        for i, row in enumerate(grid):
            rows_str += "%Row {}\n".format(i) + '&\n'.join(row) + r'\\' + '\n'

        return rows_str

    def _build_edges(self):
        h_edges = []
        v_edges = []

        edge_string = "({start}) edge [DataLine] ({end})"
        for src, target, style, label, stack, faded in self.connections:
            od_node_name = '{}-{}'.format(src, target)
            h_edges.append(edge_string.format(start=src, end=od_node_name))
            v_edges.append(edge_string.format(start=od_node_name, end=target))

        for comp_name, out_data in self.left_outs.items():
            node_name, style, label, stack = out_data
            h_edges.append(edge_string.format(start=comp_name, end=node_name))

        for comp_name, out_data in self.right_outs.items():
            node_name, style, label, stack = out_data
            h_edges.append(edge_string.format(start=comp_name, end=node_name))

        for comp_name, in_data in self.ins.items():
            node_name, style, label, stack = in_data
            v_edges.append(edge_string.format(start=comp_name, end=node_name))

        paths_str = '% Horizontal edges\n' + '\n'.join(h_edges) + '\n'

        paths_str += '% Vertical edges\n' + '\n'.join(v_edges) + ';'

        return paths_str

    def _build_process_chain(self):
        sys_names = [s[0] for s in self.comps]

        chain_str = ""

        for proc, arrow in zip(self.processes, self.process_arrows):
            chain_str += "{ [start chain=process]\n \\begin{pgfonlayer}{process} \n"
            for i, sys in enumerate(proc):
                if sys not in sys_names:
                    raise ValueError(
                        'process includes a system named "{}" but no system with that name exists.'.format(
                            sys))
                if i == 0:
                    chain_str += "\\chainin ({});\n".format(sys)
                else:
                    if arrow:
                        chain_str += "\\chainin ({}) [join=by ProcessHVA];\n".format(sys)
                    else:
                        chain_str += "\\chainin ({}) [join=by ProcessHV];\n".format(sys)
            chain_str += "\\end{pgfonlayer}\n}"

        return chain_str

    def write(self, file_name=None, build=True, cleanup=True):
        """
        Write output files for the XDSM diagram.  This produces the following:

            - {file_name}.tikz
                A file containing the TIKZ definition of the XDSM diagram.
            - {file_name}.tex
                A standalone document wrapped around an include of the TIKZ file which can
                be compiled to a pdf.
            - {file_name}.pdf
                An optional compiled version of the standalone tex file.

        Parameters
        ----------
        file_name : str
            The prefix to be used for the output files
        build : bool
            Flag that determines whether the standalone PDF of the XDSM will be compiled.
            Default is True.
        cleanup: bool
            Flag that determines if padlatex build files will be deleted after build is complete
        """
        nodes = self._build_node_grid()
        edges = self._build_edges()
        process = self._build_process_chain()

        module_path = os.path.dirname(__file__)
        diagram_styles_path = os.path.join(module_path, 'diagram_styles')

        tikzpicture_str = tikzpicture_template.format(nodes=nodes,
                                                      edges=edges,
                                                      process=process,
                                                      diagram_styles_path=diagram_styles_path)

        with open(file_name + '.tikz', 'w') as f:
            f.write(tikzpicture_str)

        tex_str = tex_template.format(nodes=nodes, edges=edges,
                                      tikzpicture_path=file_name + '.tikz',
                                      diagram_styles_path=diagram_styles_path)

        if file_name:
            with open(file_name + '.tex', 'w') as f:
                f.write(tex_str)

        if build:
            os.system('pdflatex ' + file_name + '.tex')
            if cleanup:
                for ext in ['aux', 'fdb_latexmk', 'fls', 'log']:
                    f_name = '{}.{}'.format(file_name, ext)
                    if os.path.exists(f_name):
                        os.remove(f_name)
