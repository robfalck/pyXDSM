from __future__ import print_function
import os
import numpy as np

from six import iteritems

tikzpicture_template = r"""
%%% Preamble Requirements %%%
% \usepackage{{geometry}}
% \usepackage{{amsfonts}}
% \usepackage{{amsmath}}
% \usepackage{{amssymb}}
% \usepackage{{sfmath}}
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
\usepackage{{sfmath}}
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
        self.ins[name] = ('output_'+name, style, label, stack)

    def add_output(self, name, label, style='DataIO', stack=False, side="left"):
        if side == "left":
            self.left_outs[name] = ('left_output_'+name, style, label, stack)
        elif side == "right":
            self.right_outs[name] = ('right_output_'+name, style, label, stack)

    def connect(self, src, target, label, style='DataInter', stack=False, faded=False):
        if src == target:
            raise ValueError('Can not connect component to itself')
        self.connections.append([src, target, style, label, stack, faded])

    def add_process(self, systems, arrow=True):
        self.processes.append(systems)
        self.process_arrows.append(arrow)

    def from_openmdao_group(self, arg, var_map=None, sys_map=None, vars_per_line=4,
                            output_whitelist=None):
        """
        Initializes a new XDSM from the given OpenMDAO group.

        Parameters
        ----------
        group : openmdao.api.Group or openmdao.api.Problem
            The problem or group from which the XDSM should be constructed.
        var_map : dict
            A dictionary which maps variable names to a LaTex representation.  For instance,
            to display variable m_dot in a more LaTex-based way provide
            `var_map = {'m_dot', $\dot{m}$}`
        sys_map : dict
            A dictionary which maps system names to a LaTex representation.  By default, underscores
            in system names are replaced with spaces.
        vars_per_line : int
            The number of variables to be written per line for inputs, outputs, and connections.

        """
        from openmdao.api import Problem, Group

        if isinstance(arg, Problem):
            group = arg.model
        else:
            group = arg

        # Reset all members
        self.comps = []
        self.connections = []
        self.left_outs = {}
        self.right_outs = {}
        self.ins = {}
        self.processes = []
        self.process_arrows = []

        p = Problem()
        p.model = group
        p.setup(check=False)
        p.final_setup()

        subsystems_ordered = group._subsystems_allprocs
        input_srcs = group._conn_global_abs_in2out

        connections = {
            tgt: src for tgt, src in iteritems(input_srcs) if src is not None
        }

        # src2tgts = {}
        # units = {n: data.get('units', '')
        #          for n, data in iteritems(sys._var_allprocs_abs2meta)}
        #
        # noconn_srcs = sorted((n for n in sys._var_abs_names['output']
        #                       if n not in src2tgts), reverse=True)

        inputs = group.list_inputs(out_stream=None)
        outputs = group.list_outputs(out_stream=None)

        opt = 'Optimization'
        solver = 'MDA'
        comp = 'Analysis'
        grp = 'Metamodel'
        func = 'Function'

        unconnected_outputs = set([o[0] for o in outputs])
        unconnected_inputs = set([input[0] for input in inputs])

        var_map = {} if var_map is None else var_map
        sys_map = {} if sys_map is None else sys_map

        # If provided a problem with a driver, add the design variables and constraints
        if isinstance(arg, Problem) and arg.driver is not None:
            self.add_system('opt', opt, 'Optimizer')
            print(dir(p.driver))
            print(p.driver._cons)
            print(list(p.driver._cons.keys()))
            print(list(p.driver._objs.keys()))
            for var, options in p.driver._cons.items():
                src_sys = var.split('.')[0]
                name = var.split('.')[-1]
                label = 'g({0})'.format(var_map.get(name, name))
                self.connect(src_sys, 'opt', label)

        # Add the subsystems to the XDSM
        for system in subsystems_ordered:
            if isinstance(system, Group):
                sys_type = grp
            else:
                sys_type = comp
            sys_name = sys_map.get(system.name, system.name.replace('_', r'\_'))
            self.add_system(system.name, sys_type, sys_name)

        # Organize connections so that all connections between two systems are grouped
        collected_connections = {}
        for tgt, src in iteritems(connections):
            try:
                unconnected_outputs.remove(src)
            except:
                pass
            try:
                unconnected_inputs.remove(tgt)
            except:
                pass
            name = src.split('.')[-1]
            label = var_map.get(name, '{0}'.format(name.replace('_', r'\_')))

            src_sys = src.split('.')[0]
            tgt_sys = tgt.split('.')[0]

            if src_sys != tgt_sys:
                if (src_sys, tgt_sys) not in collected_connections:
                    collected_connections[src_sys, tgt_sys] = []
                collected_connections[src_sys, tgt_sys].append(label)

        # For each pair of connected systems, add the appropriate connection info
        for (src_sys, tgt_sys) in collected_connections:
            vars = collected_connections[src_sys, tgt_sys]
            lines = []
            while vars:
                lines.append(', '.join(vars[:vars_per_line]))
                del vars[:vars_per_line]
            self.connect(src_sys, tgt_sys, lines)

        # Collect the unconnected outputs from each system
        block_outputs = {}
        for output in sorted(unconnected_outputs):
            block = output.split('.')[0]
            if block not in block_outputs:
                block_outputs[block] = set()
            name = output.split('.')[-1]
            label = var_map.get(name, name)
            block_outputs[block].add(label)

        # Add the unconnected outputs for each system
        for block in block_outputs:
            outputs = [output for output in block_outputs[block] if output_whitelist is None or output in output_whitelist]
            lines = []
            while outputs:
                lines.append(', '.join(outputs[:vars_per_line]))
                del outputs[:vars_per_line]
            self.add_output(block, lines, side='right')

        # Collect the unconnected inputs from each system
        block_inputs = {}
        for input in sorted(unconnected_inputs):
            block = input.split('.')[0]
            if block not in block_inputs:
                block_inputs[block] = set()
            name = input.split('.')[-1]
            label = var_map.get(name, name)
            block_inputs[block].add(label)

        # Add the unconnected outputs for each system
        for block in block_inputs:
            inputs = [input for input in block_inputs[block]]
            lines = []
            while inputs:
                lines.append(', '.join(inputs[:vars_per_line]))
                del inputs[:vars_per_line]
            self.add_input(block, lines)

    def _parse_label(self, label):
        if isinstance(label, (tuple, list)):
            # mod_label = r'$\substack{'
            # mod_label += r' \\ '.join(label)
            # mod_label += r'}$'
            mod_label = r'$\begin{array}{c}'
            mod_label += r' \\ '.join(label)
            mod_label += r'\end{array}$'
        else:
            mod_label = r'${}$'.format(label)

        return mod_label

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
            style=comp[1]
            if comp[3] == True: #stacking
                style += ',stack'
            if comp[4] == True: #stacking
                style += ',faded'

            label = self._parse_label(comp[2])
            node = node_str.format(style=style, node_name=comp[0], node_label=label)
            grid[i_row, j_col] = node

            row_idx_map[comp[0]] = i_row
            col_idx_map[comp[0]] = j_col

        # add all the off diagonal nodes from components
        for src, target, style, label, stack, faded in self.connections:
            src_row = row_idx_map[src]
            target_col = col_idx_map[target]

            loc = (src_row, target_col)

            style=style
            if stack == True: #stacking
                style += ',stack'
            if faded == True:
                style += ',faded'

            label = self._parse_label(label)

            node_name = '{}-{}'.format(src,target)

            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=label)

            grid[loc] = node

        # add the nodes for left outputs
        for comp_name, out_data in self.left_outs.items():
            node_name, style, label, stack = out_data
            if stack:
                style += ',stack'

            i_row = row_idx_map[comp_name]
            loc = (i_row,0)

            label = self._parse_label(label)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=label)

            grid[loc] = node

         # add the nodes for right outputs
        for comp_name, out_data in self.right_outs.items():
            node_name, style, label, stack = out_data
            if stack:
                style += ',stack'

            i_row = row_idx_map[comp_name]
            loc = (i_row,-1)
            label = self._parse_label(label)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=label)

            grid[loc] = node

        # add the inputs to the top of the grid
        for comp_name, in_data in self.ins.items():
            node_name, style, label, stack = in_data
            if stack:
                style = ',stack'

            j_col = col_idx_map[comp_name]
            loc = (0,j_col)
            label = self._parse_label(label)
            node = node_str.format(style=style,
                                   node_name=node_name,
                                   node_label=label)

            grid[loc] = node

        # mash the grid data into a string
        rows_str = ''
        for i, row in enumerate(grid):
            rows_str += "%Row {}\n".format(i) +'&\n'.join(row) + r'\\'+'\n'

        return rows_str

    def _build_edges(self):
        h_edges = []
        v_edges = []

        edge_string = "({start}) edge [DataLine] ({end})"
        for src, target, style, label, stack, faded in self.connections:
            od_node_name = '{}-{}'.format(src,target)
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
                    raise ValueError('process includes a system named "{}" but no system with that name exists.'.format(sys))
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
        # hack for windows. miketex needs linux style paths
        diagram_styles_path = diagram_styles_path.replace('\\', '/')
    
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
