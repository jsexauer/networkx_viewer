try:
    # Python 3
    import tkinter as tk
    import tkinter.messagebox as tkm
    import tkinter.simpledialog as tkd
except ImportError:
    # Python 2
    import Tkinter as tk
    import tkMessageBox as tkm
    import tkSimpleDialog as tkd



import networkx as nx

from networkx_viewer.graph_canvas import GraphCanvas
from networkx_viewer.tokens import TkPassthroughEdgeToken, TkPassthroughNodeToken


class ViewerApp(tk.Tk):
    """Example simple GUI to plot a NetworkX Graph"""
    def __init__(self, graph, **kwargs):
        """Additional keyword arguments beyond graph are passed down to the
        GraphCanvas.  See it's docs for details"""
        tk.Tk.__init__(self)
        self.geometry('600x600')
        self.title('NetworkX Viewer')

        self.columnconfigure(0, weight=1)
        self.rowconfigure(10, weight=1)

        self.canvas = GraphCanvas(graph, width=400, height=400, **kwargs)
        self.canvas.grid(row=0, column=0, rowspan=11, sticky='NESW')
        self.canvas.onNodeSelected = self.onNodeSelected
        self.canvas.onEdgeSelected = self.onEdgeSelected

        tk.Label(self, text='Node:').grid(row=0, column=1, sticky='W')
        self.node_entry = tk.Entry(self, width=10)
        self.node_entry.bind('<Return>',self.add_node)
        self.node_entry.grid(row=0, column=2, columnspan=2, sticky='NESW', pady=2)
        tk.Button(self, text='+', command=self.add_node, width=2).grid(
            row=0, column=4,sticky=tk.NW,padx=2,pady=2)

        nlsb = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.node_list = tk.Listbox(self, yscrollcommand=nlsb.set, height=5)
        self.node_list.grid(row=1, column=1, columnspan=3, sticky='NESW')
        self.node_list.bind('<Delete>',lambda e: self.node_list.delete(tk.ANCHOR))
        nlsb.config(command=self.node_list.yview)
        nlsb.grid(row=1, column=4, sticky='NWS')


        tk.Label(self, text='Filter:').grid(row=2, column=1, sticky=tk.NW)
        self.filter_key = tk.Entry(self, width=10)
        self.filter_key.grid(row=3, column=1, sticky='NSW')
        filter_op_var = tk.StringVar(self, '=')
        self.filter_op = tk.OptionMenu(self, filter_op_var, "=", '!=', ">",
                                       ">=", "<", "<=", "in", "not in")
        self.filter_op.var = filter_op_var
        self.filter_op.config(width=4)
        self.filter_op.grid(row=3, column=2, sticky='N')
        self.filter_value = tk.Entry(self, width=10)
        self.filter_value.grid(row=3, column=3, sticky='NSW')

        tk.Label(self, text='Neighbors Until:').grid(row=4, column=1, columnspan=2, sticky=tk.NW)
        self.nei_filter_key = tk.Entry(self, width=10)
        self.nei_filter_key.grid(row=5, column=1, sticky='NSW')
        nei_filter_op_var = tk.StringVar(self, '=')
        self.nei_filter_op = tk.OptionMenu(self, nei_filter_op_var, "=", '!=',
                                           ">",">=", "<", "<=", "in", "not in")
        self.nei_filter_op.var = nei_filter_op_var
        self.nei_filter_op.config(width=4)
        self.nei_filter_op.grid(row=5, column=2, sticky='N')
        self.nei_filter_value = tk.Entry(self, width=10)
        self.nei_filter_value.grid(row=5, column=3, sticky='NSW')


        tk.Label(self, text='Neighbors Levels:').grid(row=6, column=1, columnspan=2, sticky=tk.NW)
        self.level_entry = tk.Entry(self, width=4)
        self.level_entry.insert(0,'1')
        self.level_entry.grid(row=6, column=3, sticky=tk.NW, padx=5)

        tk.Button(self, text='Build New', command=self.onBuildNew).grid(
            row=7, column=1)
        tk.Button(self, text='Add to Existing').grid(row=7, column=2, columnspan=2)



        line = tk.Canvas(self, height=15, width=200)
        line.create_line(0,13,250,13)
        line.create_line(0,15,250,15)
        line.grid(row=8, column=1, columnspan=5, sticky='NESW')
        self.lbl_attr = tk.Label(self, text='Attributes',
                                 wraplength=200, anchor=tk.SW, justify=tk.LEFT)
        self.lbl_attr.grid(row=9, column=1, columnspan=4, sticky='NW')

        self.tbl_attr = PropertyTable(self, {})
        self.tbl_attr.grid(row=10, column=1, columnspan=4, sticky='NESW')

        self._build_menu()

    def _build_menu(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        view = tk.Menu(self.menubar, tearoff=0)
        view.add_command(label='Center on node...', command=self.center_on_node)
        view.add_command(label='Replot', command=self.canvas.replot)
        self.menubar.add_cascade(label='View', menu=view)

    def center_on_node(self):
        node = tkd.askstring("Node Name", "Name of node to center on:")
        self.canvas.center_on_node(node)


    def add_node(self, event=None):
        node = self.node_entry.get()

        if node.isdigit() and self.canvas.dataG.has_node(int(node)):
                node = int(node)

        if self.canvas.dataG.has_node(node):
            self.node_list.insert(tk.END, node)
            self.node_entry.delete(0, tk.END)
        else:
            tkm.showerror("Node not found", "Node '%s' not in graph."%node)

    def onBuildNew(self):
        nodes = self.node_list.get(0, tk.END)
        self.node_list.delete(0, tk.END)
        self.canvas.clear()

        if len(nodes) == 2:
            self.canvas.plot_path(nodes[0], nodes[1], levels=self.level)
        else:
            self.canvas.plot(nodes, levels=self.level)

    def goto_path(self, event):
        frm = self.node_entry.get()
        to = self.node_entry2.get()
        self.node_entry.delete(0, tk.END)
        self.node_entry2.delete(0, tk.END)

        if frm == '':
            tkm.showerror("No From Node", "Please enter a node in both "
                "boxes to plot a path.  Enter a node in only the first box "
                "to bring up nodes immediately adjacent.")
            return

        if frm.isdigit() and int(frm) in self.canvas.dataG.nodes():
            frm = int(frm)
        if to.isdigit() and int(to) in self.canvas.dataG.nodes():
            to = int(to)

        self.canvas.plot_path(frm, to, levels=self.level)

    def onNodeSelected(self, node_name, node_dict):
        self.tbl_attr.build(node_dict)
        self.lbl_attr.config(text="Attributes of node '%s'"%node_name)

    def onEdgeSelected(self, edge_name, edge_dict):
        self.tbl_attr.build(edge_dict)
        self.lbl_attr.config(text="Attributes of edge between '%s' and '%s'"%
                                    edge_name[:2])

    @property
    def level(self):
        try:
            l = int(self.level_entry.get())
        except ValueError:
            tkm.showerror("Invalid Level", "Please specify a level between "
                "greater than or equal to 0")
            raise
        return l

class TkPassthroughViewerApp(ViewerApp):
    def __init__(self, graph, **kwargs):
        ViewerApp.__init__(self, graph,
            NodeTokenClass=TkPassthroughNodeToken,
            EdgeTokenClass=TkPassthroughEdgeToken, **kwargs)


class PropertyTable(tk.Frame):
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """
    def __init__(self, parent, property_dict, *args, **kw):
        tk.Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        self.vscrollbar = vscrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.canvas = canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = tk.Frame(canvas)
        self.interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor='nw')

        self.interior.bind('<Configure>', self._configure_interior)
        self.canvas.bind('<Configure>', self._configure_canvas)

        self.build(property_dict)

    def build(self, property_dict):
        for c in self.interior.winfo_children():
            c.destroy()

        def _make_pretty(value):
            ans = str(value)
            if len(ans) > 255:
                ans = ans[:253] + '...'
            return ans
        property_dict = {_make_pretty(k): _make_pretty(v)
                            for k, v in property_dict.items()}

        # Sort by key
        dict_values = sorted(property_dict.items(), key=lambda x: x[0])

        for n,(k,v) in enumerate(dict_values):
            tk.Label(self.interior, text=k, borderwidth=1, relief=tk.SOLID,
                wraplength=75, anchor=tk.E, justify=tk.RIGHT).grid(
                row=n, column=0, sticky='nesw', padx=1, pady=1, ipadx=1)
            tk.Label(self.interior, text=v, borderwidth=1,
                wraplength=125, anchor=tk.W, justify=tk.LEFT).grid(
                row=n, column=1, sticky='nesw', padx=1, pady=1, ipadx=1)


    def _configure_interior(self, event):
        """
        track changes to the canvas and frame width and sync them,
        also updating the scrollbar
        """
        # update the scrollbars to match the size of the inner frame
        size = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
        self.canvas.config(scrollregion="0 0 %s %s" % size)
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # update the canvas's width to fit the inner frame
            self.canvas.config(width=self.interior.winfo_reqwidth())


    def _configure_canvas(self, event):
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # update the inner frame's width to fill the canvas
            self.canvas.itemconfigure(self.interior_id, width=self.canvas.winfo_width())

