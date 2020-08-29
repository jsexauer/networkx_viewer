"""
Simple TK GUI to display and interact with a NetworkX Graph

Inspired by: http://stackoverflow.com/questions/6740855/board-drawing-code-to-move-an-oval

Author: Jason Sexauer

Released under the GNU General Public License (GPL)
"""
from math import atan2, pi, cos, sin
import collections
import pickle
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

from networkx_viewer.tokens import NodeToken, EdgeToken

from functools import wraps
def undoable(func):
    """Wrapper to create a savepoint which can be revered to using the
    GraphCanvas.undo method."""
    @wraps(func)
    def _wrapper(*args, **kwargs):
        # First argument should be the graphcanvas object (ie, "self")
        self = args[0]
        if not self._undo_suspend:
            self._undo_suspend = True # Prevent chained undos
            self._undo_states.append(self.dump_visualization())
            # Anytime we do an undoable action, the redo tree gets wiped
            self._redo_states = []
            func(*args, **kwargs)
            self._undo_suspend = False
        else:
            func(*args, **kwargs)
    return _wrapper

class GraphCanvas(tk.Canvas):
    """Expandable GUI to plot a NetworkX Graph"""

    def __init__(self, graph, **kwargs):
        """
        kwargs specific to GraphCanvas:
            - NodeTokenClass = Class to instantiate for a new node
               widget.  Should be inherited from NodeToken (which is from
               tk.Canvas)
            - EdgeTokenClass = Class to instantiate for a new edge widget.
               Should be inherited from EdgeToken.
            - home_node = Node to plot around when first rendering canvas
            - levels = How many nodes out to also plot when rendering

        """
        ###
        # Deal with the graph
        ###

        # Raw data graph
        self.dataG = graph

        # Graph representting what subsect of the data graph currently being
        #  displayed.
        self.dispG = nx.MultiGraph()

        # this data is used to keep track of an
        # item being dragged
        self._drag_data = {'x': 0, 'y': 0, 'item': None}

        # This data is used to track panning objects (x,y coords)
        self._pan_data = (None, None)

        # List of filters to run whenever trying to add a node to the graph
        self._node_filters = []

        # Undo list
        self._undo_states = []
        self._redo_states = []
        self._undo_suspend = False

        # Create a display version of this graph
        # If requested, plot only within a certain level of the home node
        home_node = kwargs.pop('home_node', None)
        if home_node:
            levels = kwargs.pop('levels', 1)
            graph = self._neighbors(home_node, levels=levels, graph=graph)

        # Class to use when create a node widget
        self._NodeTokenClass = kwargs.pop('NodeTokenClass',
                                          NodeToken)
        assert issubclass(self._NodeTokenClass, NodeToken), \
            "NodeTokenClass must be inherited from NodeToken"
        self._EdgeTokenClass = kwargs.pop('EdgeTokenClass',
                                          EdgeToken)
        assert issubclass(self._EdgeTokenClass, EdgeToken), \
            "NodeTokenClass must be inherited from NodeToken"

        ###
        # Now we can do UI things
        ###
        tk.Canvas.__init__(self, **kwargs)

        self._plot_graph(graph)

        # Center the plot on the home node or first node in graph
        self.center_on_node(home_node or next(iter(graph.nodes())))

        # add bindings for clicking, dragging and releasing over
        # any object with the "node" tammg
        self.tag_bind('node', '<ButtonPress-1>', self.onNodeButtonPress)
        self.tag_bind('node', '<ButtonRelease-1>', self.onNodeButtonRelease)
        self.tag_bind('node', '<B1-Motion>', self.onNodeMotion)

        self.tag_bind('edge', '<Button-1>', self.onEdgeClick)
        self.tag_bind('edge', '<Button-3>', self.onEdgeRightClick)

        self.bind('<ButtonPress-1>', self.onPanStart)
        self.bind('<ButtonRelease-1>', self.onPanEnd)
        self.bind('<B1-Motion>', self.onPanMotion)

        self.bind_all('<MouseWheel>', self.onZoon)

    def _draw_edge(self, u, v):
        """Draw edge(s).  u and v are from self.dataG"""

        # Find display nodes associated with these data nodes
        try:
            frm_disp = self._find_disp_node(u)
            to_disp = self._find_disp_node(v)
        except NodeFiltered:
            # We're hiding one of the side of the edge.  That's ok,
            # just return silently
            return

        directed = False

        if isinstance(self.dataG, nx.MultiDiGraph):
            directed = True
            edges = self.dataG.get_edge_data(u, v)
        elif isinstance(self.dataG, nx.DiGraph):
            directed = True
            edges = {0: self.dataG.edges[u, v]}
        elif isinstance(self.dataG, nx.MultiGraph):
            edges = self.dataG.get_edge_data(u, v)
        elif isinstance(self.dataG, nx.Graph):
            edges = {0: self.dataG.edges[u, v]}
        else:
            raise NotImplementedError('Data Graph Type not Supported')




        # Figure out edge arc distance multiplier
        if len(edges) == 1:
            m = 0
        else:
            m = 15

        for key, data in edges.items():
            token = self._EdgeTokenClass(data)
            if isinstance(self.dataG, nx.MultiGraph):
                dataG_id = (u,v,key)
            elif isinstance(self.dataG, nx.Graph):
                dataG_id = (u,v)
            self.dispG.add_edge(frm_disp, to_disp, key, dataG_id=dataG_id, dispG_frm=frm_disp, token=token, m=m)

            x1,y1 = self._node_center(frm_disp)
            x2,y2 = self._node_center(to_disp)
            xa,ya = self._spline_center(x1,y1,x2,y2,m)

            token.render(host_canvas=self, coords=(x1,y1,xa,ya,x2,y2),
                         directed=directed)

            if m > 0:
                m = -m # Flip sides
            else:
                m = -(m+m)  # Go next increment out

    def _draw_node(self, coord, data_node):
        """Create a token for the data_node at the given coordinater"""
        (x,y) = coord
        data = self.dataG.nodes[data_node]

        # Apply filter to node to make sure we should draw it
        for filter_lambda in self._node_filters:
            try:
                draw_flag = eval(filter_lambda, {'u':data_node, 'd':data})
            except Exception as e:
                self._show_filter_error(filter_lambda, e)
                return
            # Filters are applied as an AND (ie, all must be true)
            # So if one is false, exit
            if draw_flag == False:
                return

        # Create token and draw node
        token = self._NodeTokenClass(self, data, data_node)
        id = self.create_window(x, y, window=token, anchor=tk.CENTER,
                                  tags='node')
        self.dispG.add_node(id, dataG_id=data_node,
                                 token_id=id, token=token)
        return id

    def _get_id(self, event, tag='node'):
        for item in self.find_overlapping(event.x-1, event.y-1,
                                                 event.x+1, event.y+1):
            if tag in self.gettags(item):
                return item
        raise Exception('No Token Found')

    def _node_center(self, item_id):
        """Calcualte the center of a given node"""
        b = self.bbox(item_id)
        return ( (b[0]+b[2])/2, (b[1]+b[3])/2 )

    def _spline_center(self, x1, y1, x2, y2, m):
        """Given the coordinate for the end points of a spline, calcuate
        the mipdoint extruded out m pixles"""
        a = (x2 + x1)/2
        b = (y2 + y1)/2
        beta = (pi/2) - atan2((y2-y1), (x2-x1))

        xa = a - m*cos(beta)
        ya = b + m*sin(beta)
        return (xa, ya)


    def _neighbors(self, node, levels=1, graph=None):
        """Return graph of neighbors around node in graph (default: self.dataG)
        to a certain number of levels"""

        if graph is None:
            graph = self.dataG

        if not isinstance(node, (list, tuple, set)):
            node = [node,]

        neighbors = set(node)
        blocks = [[n,] for n in node]
        for i in range(levels):
            for n in neighbors:
                new_neighbors = set(graph.neighbors(n)) - neighbors
                blocks.append(new_neighbors)
                neighbors = neighbors.union(new_neighbors)
        G = graph.subgraph(neighbors)

        if len(blocks) > 1:
            # Create a block repersentation of our graph and make sure we're plotting
            #  anything that connects the blocks too

            # Create blocks for each individual node not already in a block
            non_blocked = set(self.dataG.nodes()) - neighbors
            non_blocked = [[a,] for a in non_blocked]

            partitions = blocks + non_blocked

            # B = nx.blockmodel(graph, partitions)
            B = nx.quotient_graph(graph, partitions, relabel=True)

            # The resulting graph will has nodes numbered according their index in partitions
            # We want to go through the partitions which are blocks and find the shortest path

            num_blocks = len(blocks)
            for frm_node, to_node in zip(range(num_blocks), range(1,num_blocks-1)):
                try:
                    path = nx.shortest_path(B, frm_node, to_node)
                except nx.NetworkXNoPath as e:
                    pass # In an island, which is permissible
                except nx.NodeNotFound as e2:
                    pass # Node reduced away, which is permissible
                except nx.NetworkXError as e:
                    tkm.showerror("Node not in graph", str(e))
                    return
                else:
                    # Break path in B back down into path in G
                    path2 = []
                    for a in path[1:-1]: # don't include end points
                        for n in partitions[a]:
                            neighbors.add(n)
            G = graph.subgraph(neighbors)


        return G

    def _radial_behind(self, home_node, behind_node):
        """Detect what nodes create a radial string behind the edge from
        home_node to behind_node"""

        base_islands = nx.number_connected_components(self.dispG)

        # If we remove the edge in question, it should radialize the system
        #  and we can then detect the side to remove
        G = nx.Graph()
        G.add_nodes_from(self.dispG.nodes())
        G.add_edges_from(self.dispG.edges())
        G.remove_edge(home_node, behind_node)

        node_sets = list(nx.connected_components(G))

        if len(node_sets) == base_islands:
            # There is no radial path behind this node
            return None
        else:
            for ns in node_sets:
                if behind_node in ns:
                    # We know know what nodes to remove from the display graph
                    #  to remove the radial string
                    return ns

    def add_filter(self, filter_lambda):
        # Evaluate filter against all currently displayed nodes.  If
        #  any of them do not pass, hide them
        nodes_to_hide = []
        for n, d in self.dispG.nodes(data=True):
            dataG_id = d['dataG_id']
            try:
                show_flag = eval(filter_lambda,
                             {'u':dataG_id, 'd':self.dataG.nodes[dataG_id]})
            except Exception as e:
                self._show_filter_error(filter_lambda, e)
                return False
            if show_flag == False:
                nodes_to_hide.append(n)

        # Hide the nodes
        for n in nodes_to_hide:
            self.hide_node(n)

        # Add this filter to the filter list so that any future plots include
        # this filter
        self._node_filters.append(filter_lambda)
        return True

    def remove_filter(self, filter_lambda):
        self._node_filters.remove(filter_lambda)

    def _show_filter_error(self, filter_lambda, e):
        tkm.showerror("Invalid Filter",
              "Evaluating the filter lambda function\n" +
              filter_lambda + "\n\nraised the following " +
              "exception:\n\n" + str(e))

    @undoable
    def onPanStart(self, event):
        self._pan_data = (event.x, event.y)
        self.winfo_toplevel().config(cursor='fleur')

    def onPanMotion(self, event):
        # compute how much to move
        delta_x = event.x - self._pan_data[0]
        delta_y = event.y - self._pan_data[1]
        self.move(tk.ALL, delta_x, delta_y)

        # Record new location
        self._pan_data = (event.x, event.y)

    def onPanEnd(self, event):
        self._pan_data = (None, None)
        self.winfo_toplevel().config(cursor='arrow')

    def onZoon(self, event):
        factor = 0.1 * (1 if event.delta < 0 else -1)

        # Translate root coordinates into relative coordinates
        x = (event.widget.winfo_rootx() + event.x) - self.winfo_rootx()
        y = (event.widget.winfo_rooty() + event.y) - self.winfo_rooty()

        # Move everyone proportional to how far they are from the cursor
        ids = self.find_withtag('node') # + self.find_withtag('edge')

        for i in ids:
            ix, iy, t1, t2 = self.bbox(i)

            dx = (x-ix)*factor
            dy = (y-iy)*factor

            self.move(i, dx, dy)

        # Redraw all the edges
        for to_node, from_node, data in self.dispG.edges(data=True):
            from_xy = self._node_center(from_node)
            to_xy = self._node_center(to_node)
            if data['dispG_frm'] != from_node:
                # Flip!
                a = from_xy[:]
                from_xy = to_xy[:]
                to_xy = a[:]
            spline_xy = self._spline_center(*from_xy+to_xy+(data['m'],))

            data['token'].coords((from_xy+spline_xy+to_xy))


    @undoable
    def onNodeButtonPress(self, event):
        """Being drag of an object"""
        # record the item and its location
        item = self._get_id(event)
        self._drag_data["item"] = item
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

        dataG_id = self.dispG.nodes(data=True)[item]['dataG_id']

        self.onNodeSelected(dataG_id, self.dataG.nodes[dataG_id])


    def onNodeSelected(self, node_name, node_data):
        """Overwrite with custom function in external UI"""
        pass

    def onNodeButtonRelease(self, event):
        """End drag of an object"""

        # reset the drag information
        self._drag_data['item'] = None
        self._drag_data['x'] = 0
        self._drag_data['y'] = 0


    def onNodeMotion(self, event):
        """Handle dragging of an object"""
        if self._drag_data['item'] is None:
            return
        # compute how much this object has moved
        delta_x = event.x - self._drag_data['x']
        delta_y = event.y - self._drag_data['y']
        # move the object the appropriate amount
        self.move(self._drag_data['item'], delta_x, delta_y)
        # record the new position
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

        # Redraw any edges
        from_node = self._drag_data['item']
        from_xy = self._node_center(from_node)
        for _, to_node, edge in self.dispG.edges(from_node, data=True):
            to_xy = self._node_center(to_node)
            if edge['dispG_frm'] != from_node:
                # Flip!
                spline_xy = self._spline_center(*to_xy+from_xy+(edge['m'],))
                edge['token'].coords((to_xy+spline_xy+from_xy))
            else:
                spline_xy = self._spline_center(*from_xy+to_xy+(edge['m'],))
                edge['token'].coords((from_xy+spline_xy+to_xy))

    def onTokenRightClick(self, event):
        item = self._get_id(event)

        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Grow', command=lambda: self.grow_node(item),
                              accelerator='G')
        popup.add_command(label='Grow until...',
                          command=lambda: self.grow_until(item))
        popup.add_command(label='Mark', command=lambda: self.mark_node(item),
                              accelerator='M')
        popup.add_command(label='Hide', command=lambda: self.hide_node(item),
                              accelerator='H')

        hide_behind = tk.Menu(popup, tearoff=0)
        for _, n in self.dispG.edges(item):
            assert _ == item
            if self._radial_behind(item, n):
                state = tk.ACTIVE
            else:
                state = tk.DISABLED
            hide_behind.add_command(label=str(self.dispG.nodes[n]['dataG_id']),
                  state=state,
                  command=lambda item=item, n=n: self.hide_behind(item, n))

        popup.add_cascade(label='Hide Behind', menu=hide_behind)

        token = self.dispG.nodes[item]['token']
        token.customize_menu(popup, item)

        try:
            popup.post(event.x_root, event.y_root)
        finally:
            popup.grab_release()


    def hide_behind(self, home_node, behind_node):
        """Hide radial string behind edge from home_node to behind_node"""
        nodes = self._radial_behind(home_node, behind_node)

        if nodes is None:
            raise ValueError('No radial string detected')
        for n in nodes:
            self.hide_node(n)

    def onNodeKey(self, event):
        item = self._get_id(event)
        cmd = event.char.upper()

        if cmd == 'G':
            self.grow_node(item)
        elif cmd == 'H':
            self.hide_node(item)
        elif cmd == 'M':
            self.mark_node(item)

    @undoable
    def grow_node(self, disp_node, levels=1):
        data_node = self.dispG.nodes(data=True)[disp_node]['dataG_id']

        grow_graph = self._neighbors(data_node, levels)

        self._plot_additional(grow_graph.nodes())

    @undoable
    def grow_until(self, disp_node, stop_condition=None, levels=0):

        # Find condition to stop growing
        if stop_condition is None:
            stop_condition = tkd.askstring("Stop Condition", "Enter lambda "
                "function which returns True when stop condition is met.\n"
                "Parameters are:\n  - u, the node's name, and \n  "
                "- d, the data dictionary.\n\nExample: "
                "d['color']=='red' \nwould grow until a red node is found.")

            if stop_condition is None: return

        data_node = self.dispG.nodes(data=True)[disp_node]['dataG_id']
        existing_data_nodes = set([ v['dataG_id']
                                    for k,v in self.dispG.nodes(data=True) ])

        max_iters = 10
        stop_node = None    # Node which met stop condition
        grow_nodes = set([data_node])   # New nodes
        # Iterate until we find a node that matches the stop condition (or,
        #  worst case, we reach max iters)
        for i in range(1,max_iters+1):
            old_grow_nodes = grow_nodes.copy()
            grow_nodes.clear()
            for n in old_grow_nodes:
                grow_graph = self._neighbors(n, levels=i)
                grow_nodes = grow_nodes.union(set(grow_graph.nodes())) - \
                             existing_data_nodes - old_grow_nodes
            if len(grow_nodes) == 0:
                # Start out next iteration with the entire graph
                grow_nodes = existing_data_nodes.copy()
                continue
            for u in grow_nodes:
                d = self.dataG.nodes[u]
                try:
                    stop = eval(stop_condition, {'u':u, 'd':d})
                except Exception as e:
                    tkm.showerror("Invalid Stop Condition",
                                  "Evaluating the stop condition\n\n" +
                                  stop_condition + "\n\nraise the following " +
                                  "exception:\n\n" + str(e))
                    return
                if stop:
                    stop_node = u
                    break
            if stop_node is not None:
                break
        if stop_node is None:
            tkm.showerror("Stop Condition Not Reached", "Unable to find a node "
            "which meet the stop condition within %d levels."%i)
            return

        ## Grow the number of times it took to find the node
        #self.grow_node(disp_node, i)

        # Find shortest path to stop_node
        self.plot_path(data_node, stop_node, levels=levels, add_to_exsting=True)

    @undoable
    def hide_node(self, disp_node):

        # Remove all the edges from display
        for n, m, d in self.dispG.edges(disp_node, data=True):
            d['token'].delete()

        # Remove the node from display
        self.delete(disp_node)

        # Remove the node from dispG
        self.dispG.remove_node(disp_node)

        self._graph_changed()

    @undoable
    def mark_node(self, disp_node):
        """Mark a display node"""
        token = self.dispG.nodes(data=True)[disp_node]['token']
        token.mark()

    @undoable
    def center_on_node(self, data_node):
        """Center canvas on given **DATA** node"""
        try:
            disp_node = self._find_disp_node(data_node)
        except ValueError as e:
            tkm.showerror("Unable to find node", str(e))
            return
        x,y = self.coords(self.dispG.nodes[disp_node]['token_id'])

        # Find center of canvas
        w = self.winfo_width()/2
        h = self.winfo_height()/2
        if w < 1:
            # We haven't been drawn yet
            w = int(self['width'])/2
            h = int(self['height'])/2

        # Calc delta to move to center
        delta_x = w - x
        delta_y = h - y

        self.move(tk.ALL, delta_x, delta_y)

    def onEdgeRightClick(self, event):
        item = self._get_id(event, 'edge')
        for u,v,k,d in self.dispG.edges(keys=True, data=True):
            if d['token'].id == item:
                break

        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Mark', command=lambda: self.mark_edge(u,v,k))
        d['token'].customize_menu(popup)

        try:
            popup.post(event.x_root, event.y_root)
        finally:
            popup.grab_release()

    def onEdgeClick(self, event):
        item = self._get_id(event, 'edge')
        for u,v,k,d in self.dispG.edges(keys=True, data=True):
            if d['token'].id == item:
                break
        dataG_id = self.dispG.edges[u, v, k]['dataG_id']
        self.onEdgeSelected(dataG_id, self.dataG.get_edge_data(*dataG_id))

    def onEdgeSelected(self, edge_name, edge_data):
        """Overwrite with custom function in external UI"""
        pass

    def hide_edge(self, edge_id):
        # This feature breaks the "grow" feature.  Also I've decided I kind of
        #  don't like it as it's decieving to have both nodes on the display
        #  but not be showing an edge between them
        raise NotImplementedError()
        for u, v, d in self.dispG.edges(data=True):
            if d['token_id']==edge_id:
                self.dispG.remove_edge(u,v)
                break
        self.delete(edge_id)
        self._graph_changed()

    @undoable
    def mark_edge(self, disp_u, disp_v, key):
        token = self.dispG[disp_u][disp_v][key]['token']
        token.mark()


    def clear(self):
        """Clear the canvas and display graph"""
        self.delete(tk.ALL)
        self.dispG.clear()

    @undoable
    def plot(self, home_node, levels=1):
        """Plot node (from dataG) out to levels.  home_node can be list of nodes."""
        self.clear()

        graph = self._neighbors(home_node, levels=levels)
        self._plot_graph(graph)

        if isinstance(home_node, (list, tuple, set)):
            self.center_on_node(home_node[0])
        else:
            self.center_on_node(home_node)

    @undoable
    def plot_additional(self, home_nodes, levels=0):
        """Add nodes to existing plot.  Prompt to include link to existing
        if possible.  home_nodes are the nodes to add to the graph"""

        new_nodes = self._neighbors(home_nodes, levels=levels)
        new_nodes = home_nodes.union(new_nodes)

        displayed_data_nodes = set([ v['dataG_id']
                            for k,v in self.dispG.nodes.items() ])

        # It is possible the new nodes create a connection with the existing
        #  nodes; in such a case, we don't need to try to find the shortest
        #  path between the two blocks
        current_num_islands = nx.number_connected_components(self.dispG)
        new_num_islands = nx.number_connected_components(
            self.dataG.subgraph(displayed_data_nodes.union(new_nodes)))
        if new_num_islands > current_num_islands:
            # Find shortest path between two blocks graph and, if it exists,
            #  ask the user if they'd like to include those nodes in the
            #  display as well.
            # First, create a block model of our data graph where what is
            #  current displayed is a block, the new nodes are a a block
            all_nodes = set(self.dataG.nodes())
            singleton_nodes = all_nodes - displayed_data_nodes - new_nodes
            singleton_nodes = map(lambda x: [x], singleton_nodes)
            partitions = [displayed_data_nodes, new_nodes] + \
                         list(singleton_nodes)
            #B = nx.blockmodel(self.dataG, partitions, multigraph=True)
            B = nx.quotient_graph(self.dataG, partitions, relabel=True)

            # Find shortest path between existing display (node 0) and
            #  new display island (node 1)
            try:
                path = nx.shortest_path(B, 0, 1)
            except nx.NetworkXNoPath:
                pass
            else:
                ans = tkm.askyesno("Plot path?", "A path exists between the "
                  "currently graph and the nodes you've asked to be added "
                  "to the display.  Would you like to plot that path?")
                if ans: # Yes to prompt
                    # Add the nodes from the source graph which are part of
                    #  the path to the new_nodes set
                    # Don't include end points because they are the two islands
                    for u in path[1:-1]:
                        Gu = B.nodes[u]['graph'].nodes()
                        assert len(Gu) == 1; Gu = list(Gu)[0]
                        new_nodes.add(Gu)

        # Plot the new nodes
        self._plot_additional(new_nodes)

    def dump_visualization(self):
        """Record currently visable nodes, their position, and their widget's
        state.  Used by undo functionality and to memorize speicific displays"""

        ans = self.dispG.copy()

        # Add current x,y info to the graph
        for n, d in ans.nodes(data=True):
            (d['x'],d['y']) = self.coords(d['token_id'])

        # Pickle the whole thing up
        ans = pickle.dumps(ans)

        return ans

    def load_visualization(self, dump):
        """Load a visualization as created by dump_visulaization method"""
        # Unpickle string into nx graph
        G = pickle.loads(dump)

        # Clear us and rebuild
        self.clear()
        bad_nodes = set()
        for n, d in G.nodes(data=True):
            try:
                id = self._draw_node((d['x'],d['y']), d['dataG_id'])
            except KeyError as e:
                tkm.showerror("Model Error",
                "Substation no longer exists: %s" % e)
                bad_nodes.add(e.message)
                continue
            state = d['token'].__getstate__()
            self.dispG.nodes[id]['token']._setstate(state)

        for u, v in set(G.edges()):
            # Find dataG ids from old dispG
            uu = G.nodes[u]['dataG_id']
            vv = G.nodes[v]['dataG_id']
            if uu in bad_nodes: continue
            if vv in bad_nodes: continue
            try:
                self._draw_edge(uu,vv)
            except KeyError as e:
                tkm.showerror("Model Error",
                "Model no longer the same around %s" % e)
                continue

            state = d['token'].__getstate__()
            self.dispG.nodes[id]['token']._setstate(state)

            # Find new dispG ids from dataG ids
            uuu = self._find_disp_node(uu)
            vvv = self._find_disp_node(vv)

            # Set state for the new edge(s)
            for k, ed in self.dispG.get_edge_data(uuu, vvv).items():
                try:
                    state = G.edges[u, v, k]['token'].__getstate__()
                except KeyError as e:
                    tkm.showerror("Model Error",
                    "Line different between models: %s" % e)
                ed['token']._setstate(state)

        self.refresh()

    def undo(self):
        """Undoes the last action marked with the undoable decorator"""
        try:
            state = self._undo_states.pop()
        except IndexError:
            # No undoable states (empty list)
            return
        self._redo_states.append(self.dump_visualization())
        self.load_visualization(state)

    def redo(self):
        try:
            state = self._redo_states.pop()
        except IndexError:
            # No redoable states
            return
        self.load_visualization(state)

    @undoable
    def replot(self):
        """Replot existing nodes, hopefully providing a better layout"""
        nodes = [d['dataG_id'] for n, d in self.dispG.nodes(data=True)]

        # Remember which nodes and edges were marked
        nodes_marked = [d['dataG_id']
                        for n, d in self.dispG.nodes(data=True)
                        if d['token'].is_marked]
        edges_marked = [d['dataG_id']
                        for u,v,k,d in self.dispG.edges(data=True, keys=True)
                        if d['token'].is_marked]
        # Replot
        self.plot(nodes, levels=0)

        # Remark
        for n in nodes_marked:
            self.mark_node(self._find_disp_node(n))
        edge_map = {d['dataG_id']: (u,v,k)
                    for u,v,k,d in self.dispG.edges(data=True, keys=True)}
        for dataG_id in edges_marked:
            self.mark_edge(*edge_map[dataG_id])

    def refresh(self):
        """Redrawn nodes and edges, updating any display attributes that
        maybe have changed in the underlying tokens.
        This method should be called anytime the underling data graph changes"""

        # Edges
        for u,v,k,d in self.dispG.edges(keys=True, data=True):
            token = d['token']
            dataG_id = d['dataG_id']
            token.edge_data = self.dataG.get_edge_data(*dataG_id)
            token.itemconfig()  # Refreshed edge's display

        # Nodes
        for u, d in self.dispG.nodes(data=True):
            token = d['token']
            node_name = d['dataG_id']
            data = self.dataG.nodes[node_name]
            token.render(data, node_name)

        # Update fully expanded status
        self._graph_changed()


    @undoable
    def plot_path(self, frm_node, to_node, levels=1, add_to_exsting=False):
        """Plot shortest path between two nodes"""
        try:
            path = nx.shortest_path(self.dataG, frm_node, to_node)
        except nx.NetworkXNoPath as e:
            tkm.showerror("No path", str(e))
            return
        except nx.NodeNotFound as e:
            tkm.showerror("No path", str(e))
            return
        except nx.NetworkXError as e:
            tkm.showerror("Node not in graph", str(e))
            return

        graph = self.dataG.subgraph(self._neighbors(path,levels=levels))

        if add_to_exsting:
            self._plot_additional(graph.nodes())
        else:
            self.clear()
            self._plot_graph(graph)

        # Mark the path
        if levels > 0 or add_to_exsting:
            for u, v in zip(path[:-1], path[1:]):
                u_disp = self._find_disp_node(u)
                v_disp = self._find_disp_node(v)
                for key, value in self.dispG.get_edge_data(u_disp, v_disp).items():
                    self.mark_edge(u_disp, v_disp, key)



    def _plot_graph(self, graph):
        # Create nodes
        scale = min(self.winfo_width(), self.winfo_height())
        if scale == 1:
            # Canvas not initilized yet; use height and width hints
            scale = int(min(self['width'], self['height']))

        scale -= 50
        if len(graph) > 1:
            layout = self.create_layout(graph, scale=scale, min_distance=50)

            # Find min distance between any node and make sure that is at least
            #  as big as
            for n in graph.nodes():
                self._draw_node(layout[n]+20, n)
        else:
            self._draw_node((scale/2, scale/2), list(graph.nodes())[0])

        # Create edges
        for frm, to in set(graph.edges()):
            self._draw_edge(frm, to)

        self._graph_changed()

    def _plot_additional(self, nodes):
        """Add a set of nodes to the graph, kepping all already
        existing nodes in the graph.  This private method plots only litterally
        the nodes requested.  It does not check to see if a path exists between
        the existing nodes and the new nodes; use plot_additional (without
        preceding underscore) to perform this check."""
        # We also need grow_graph to include nodes which are already
        # ploted but are not immediate neighbors, so that we can successfully
        # capture their edges.  To do this, we should subgraph the data graph
        # using the nodes of the grow graph and existing data nodes
        existing_data_nodes = set([ v['dataG_id']
                            for k,v in self.dispG.nodes.items() ])
        nodes = set(nodes).union(existing_data_nodes)
        grow_graph = self.dataG.subgraph(nodes)

        # Build layout considering existing nodes and
        #  argument to center around the home node (ie, "disp_node")
        fixed = {}
        for n,d in self.dispG.nodes(data=True):
            fixed[d['dataG_id']] = self.coords(n)

        layout = self.create_layout(grow_graph,
                                    pos=fixed, fixed=list(fixed.keys()))

        # Unfreeze graph
        grow_graph = type(grow_graph)(grow_graph)

        # Filter the graph to only include new edges
        for n,m in grow_graph.copy().edges():
            if (n in existing_data_nodes) and (m in existing_data_nodes):
                grow_graph.remove_edge(n,m)

        # Remove any nodes which connected to only existing nodes (ie, they
        #  they connect to nothing else in grow_graph)
        for n, degree in grow_graph.copy().degree():
            if degree == 0:
                grow_graph.remove_node(n)

        if len(grow_graph.nodes()) == 0:
            # No new nodes to add
            return

        # Plot the new nodes and add to the disp graph
        for n in grow_graph.nodes():
            if n in existing_data_nodes: continue
            self._draw_node(layout[n], n)

        for n, m in set(grow_graph.edges()):
            if (n in existing_data_nodes) and (m in existing_data_nodes):
                continue

            # Add edge to dispG and draw
            self._draw_edge(n, m)

        self._graph_changed()


    def _graph_changed(self):
        """Handle token callbacks
        Called every time a node or edge has been added or removed from
        the display graph.  Used to propagate completeness indicators
        down to the node's tokens"""

        for n, d in self.dispG.nodes(data=True):
            token = d['token']
            if self.dispG.degree(n) == self.dataG.degree(d['dataG_id']):
                token.mark_complete()
            else:
                token.mark_incomplete()


    def _find_disp_node(self, data_node):
        """Given a node's name in self.dataG, find in self.dispG"""
        disp_node = [a for a, d in self.dispG.nodes(data=True)
                    if d['dataG_id'] == data_node]
        if len(disp_node) == 0 and str(data_node).isdigit():
            # Try again, this time using the int version
            data_node = int(data_node)
            disp_node = [a for a, d in self.dispG.nodes(data=True)
                    if d['dataG_id'] == data_node]

        if len(disp_node) == 0:
            # It could be that this node is not displayed because it is
            #  currently being filtered out.  Test for that and, if true,
            #  raise a NodeFiltered exception
            for f in self._node_filters:
                try:
                    show_flag = eval(f, {'u':data_node,
                                         'd':self.dataG.nodes[data_node]})
                except Exception as e:
                    # Usually we we would alert user that eval failed, but
                    #  in this case, we're doing this without their knowlage
                    #  so we're just going to die silently
                    break
                if show_flag == False:
                    raise NodeFiltered
            raise ValueError("Data Node '%s' is not currently displayed"%\
                                data_node)
        elif len(disp_node) != 1:
            raise AssertionError("Data node '%s' is displayed multiple "
                                    "times" % data_node)
        return disp_node[0]

    def create_layout(self, G, pos=None, fixed=None, scale=1.0,
                      min_distance=None):
        """Position nodes using Fruchterman-Reingold force-directed algorithm.

        Parameters
        ----------
        G : NetworkX graph

        dim : int
           Dimension of layout

        k : float (default=None)
           Optimal distance between nodes.  If None the distance is set to
           1/sqrt(n) where n is the number of nodes.  Increase this value
           to move nodes farther apart.


        pos : dict or None  optional (default=None)
           Initial positions for nodes as a dictionary with node as keys
           and values as a list or tuple.  If None, then nuse random initial
           positions.

        fixed : list or None  optional (default=None)
          Nodes to keep fixed at initial position.

        iterations : int  optional (default=50)
           Number of iterations of spring-force relaxation

        weight : string or None   optional (default='weight')
            The edge attribute that holds the numerical value used for
            the edge weight.  If None, then all edge weights are 1.

        scale : float (default=1.0)
            Scale factor for positions. The nodes are positioned
            in a box of size [0,scale] x [0,scale].

        min_distance : float   optional (default=None)
            Minimum distance to enforce between nodes.  If passed with scale,
            this may cause the returned positions to go outside the scale.

        Returns
        -------
        dict :
           A dictionary of positions keyed by node

        Examples
        --------
        >>> G=nx.path_graph(4)
        >>> pos=nx.spring_layout(G)

        # The same using longer function name
        >>> pos=nx.fruchterman_reingold_layout(G)
        """
        # This is a modification of the networkx.layout library's
        #  fruchterman_reingold_layout to work well with fixed positions
        #  and large inital positions (not near 1.0).  This involved
        #  modification to what the optimal "k" is and the removal of
        #  the resize when fixed is passed
        dim = 2

        try:
            import numpy as np
        except ImportError:
            raise ImportError("fruchterman_reingold_layout() requires numpy: http://scipy.org/ ")
        if fixed is not None:
            nfixed=dict(zip(G,range(len(G))))
            fixed=np.asarray([nfixed[v] for v in fixed])

        if pos is not None:
            # Determine size of exisiting domain
            dom_size = max(flatten(pos.values()))
            pos_arr=np.asarray(np.random.random((len(G),dim)))*dom_size
            for i,n in enumerate(G):
                if n in pos:
                    pos_arr[i]=np.asarray(pos[n])
        else:
            pos_arr=None
            dom_size = 1.0

        if len(G)==0:
            return {}
        if len(G)==1:
            return {G.nodes()[0]:(1,)*dim}

        A=nx.to_numpy_matrix(G)
        nnodes,_ = A.shape
        # I've found you want to occupy about a two-thirds of the window size
        if fixed is not None:
            k=(min(self.winfo_width(), self.winfo_height())*.66)/np.sqrt(nnodes)
        else:
            k = None

        # Alternate k, for when vieweing the whole graph, not a subset
        #k=dom_size/np.sqrt(nnodes)
        pos=self._fruchterman_reingold(A,dim,k,pos_arr,fixed)

        if fixed is None:
            # Only rescale non fixed layouts
            pos= nx.layout.rescale_layout(pos,scale=scale)

        if min_distance and fixed is None:
            # Find min distance between any two nodes and scale such that
            #  this distance = min_distance

            # matrix of difference between points
            delta = np.zeros((pos.shape[0],pos.shape[0],pos.shape[1]),
                             dtype=A.dtype)
            for i in range(pos.shape[1]):
                delta[:,:,i]= pos[:,i,None]-pos[:,i]
            # distance between points
            distance=np.sqrt((delta**2).sum(axis=-1))

            cur_min_dist = np.where(distance==0, np.inf, distance).min()

            if cur_min_dist < min_distance:
                # calculate scaling factor and rescale
                rescale = (min_distance / cur_min_dist) * pos.max()

                pos = nx.layout.rescale_layout(pos, scale=rescale)

        return dict(zip(G,pos))

    def _fruchterman_reingold(self, A, dim=2, k=None, pos=None, fixed=None,
                              iterations=50):
        # Position nodes in adjacency matrix A using Fruchterman-Reingold
        # Entry point for NetworkX graph is fruchterman_reingold_layout()
        try:
            import numpy as np
        except ImportError:
            raise ImportError("_fruchterman_reingold() requires numpy: http://scipy.org/ ")

        try:
            nnodes,_=A.shape
        except AttributeError:
            raise nx.NetworkXError(
                "fruchterman_reingold() takes an adjacency matrix as input")

        A=np.asarray(A) # make sure we have an array instead of a matrix

        if pos is None:
            # random initial positions
            pos=np.asarray(np.random.random((nnodes,dim)),dtype=A.dtype)
        else:
            # make sure positions are of same type as matrix
            pos=pos.astype(A.dtype)

        # optimal distance between nodes
        if k is None:
            k=np.sqrt(1.0/nnodes)
        # the initial "temperature"  is about .1 of domain area (=1x1)
        # this is the largest step allowed in the dynamics.
        # Modified to actually detect for domain area
        t = max(max(pos.T[0]) - min(pos.T[0]), max(pos.T[1]) - min(pos.T[1]))*0.1
        # simple cooling scheme.
        # linearly step down by dt on each iteration so last iteration is size dt.
        dt=t/float(iterations+1)
        delta = np.zeros((pos.shape[0],pos.shape[0],pos.shape[1]),dtype=A.dtype)
        # the inscrutable (but fast) version
        # this is still O(V^2)
        # could use multilevel methods to speed this up significantly
        for iteration in range(iterations):
            # matrix of difference between points
            for i in range(pos.shape[1]):
                delta[:,:,i]= pos[:,i,None]-pos[:,i]
            # distance between points
            distance=np.sqrt((delta**2).sum(axis=-1))
            # enforce minimum distance of 0.01
            distance=np.where(distance<0.01,0.01,distance)
            # displacement "force"
            displacement=np.transpose(np.transpose(delta)*\
                                      (k*k/distance**2-A*distance/k))\
                                      .sum(axis=1)
            # update positions
            length=np.sqrt((displacement**2).sum(axis=1))
            length=np.where(length<0.01,0.1,length)
            delta_pos=np.transpose(np.transpose(displacement)*t/length)
            if fixed is not None:
                # don't change positions of fixed nodes
                delta_pos[fixed]=0.0
            pos+=delta_pos
            # cool temperature
            t-=dt
            ###pos=_rescale_layout(pos)
        return pos

class NodeFiltered(Exception):
    pass

def flatten(l):
    try:
        bs = basestring
    except NameError:
        # Py3k
        bs = str
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, bs):
            for sub in flatten(el):
                yield sub
        else:
            yield el
