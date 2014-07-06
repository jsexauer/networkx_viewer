try:
    # Python 3
    import tkinter as tk
    import tkinter.messagebox as tkm
except ImportError:
    # Python 2
    import Tkinter as tk
    import tkMessageBox as tkm



import networkx as nx

from networkx_viewer.graph_canvas import GraphCanvas
from networkx_viewer.tokens import TkPassthroughEdgeToken, TkPassthroughNodeToken


class ViewerApp(tk.Tk):
    """Example simple GUI to plot a NetworkX Graph"""
    def __init__(self, graph, **kwargs):
        """Additional keywork arguments beyond graph are passed down to the
        GraphCanvas.  See it's docs for details"""
        tk.Tk.__init__(self)
        self.geometry('400x400')
        self.title('NetworkX Viewer')

        self.columnconfigure(3, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = GraphCanvas(graph, width=400, height=400, **kwargs)
        self.canvas.grid(row=0, column=0, columnspan=5, sticky='NESW')

        tk.Label(self, text='Node(s):').grid(row=1, column=0, sticky=tk.NW)
        self.node_entry = tk.Entry(self, width=10)
        self.node_entry.bind('<Return>',self.goto_node)
        self.node_entry.grid(row=1, column=1, sticky=tk.NW)

        tk.Label(self, text='  ').grid(row=1, column=2, sticky=tk.NW)
        self.node_entry2 = tk.Entry(self, width=10)
        self.node_entry2.bind('<Return>',self.goto_path)
        self.node_entry2.grid(row=1, column=3, sticky=tk.NW)

        tk.Label(self, text='Levels:').grid(row=1, column=3, sticky=tk.NE)
        self.level_entry = tk.Entry(self, width=4)
        self.level_entry.insert(0,'1')
        self.level_entry.bind('<Return>',self.goto_node)
        self.level_entry.grid(row=1, column=4, sticky=tk.NE, padx=5)

    def goto_node(self, event):
        # Detect to see if we should actually use goto_path
        if self.node_entry.get() != '' and self.node_entry2.get() != '':
            return self.goto_path(event)

        self.canvas.clear()

        node = self.node_entry.get()
        self.node_entry.delete(0, tk.END)

        if node.isdigit():
            try:
                self.canvas.plot(int(node), levels=self.level)
            except nx.NetworkXError:
                pass
            else:
                return
        try:
            self.canvas.plot(node, levels=max(self.level,1))
        except nx.NetworkXError:
            tkm.showerror("Node not found", "Node '%s' not in graph."%node)

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
