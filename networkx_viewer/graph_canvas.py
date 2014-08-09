"""
Simple TK GUI to display and interact with a NetworkX Graph

Inspired by: http://stackoverflow.com/questions/6740855/board-drawing-code-to-move-an-oval

Author: Jason Sexauer

Released under the GNU General Public License (GPL)
"""
from math import atan2, pi, cos, sin
import collections
try:
    # Python 3
    import tkinter as tk
    import tkinter.messagebox as tkm
except ImportError:
    # Python 2
    import Tkinter as tk
    import tkMessageBox as tkm

import networkx as nx

from networkx_viewer.tokens import NodeToken, EdgeToken

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

        

        # add bindings for clicking, dragging and releasing over
        # any object with the "node" tammg
        self.tag_bind('node', '<ButtonPress-1>', self.onNodeButtonPress)
        self.tag_bind('node', '<ButtonRelease-1>', self.onNodeButtonRelease)
        self.tag_bind('node', '<B1-Motion>', self.onNodeMotion)
        
        self.tag_bind('edge', '<Button-3>', self.onEdgeRightClick)

        self.bind('<ButtonPress-1>', self.onPanStart)
        self.bind('<ButtonRelease-1>', self.onPanEnd)
        self.bind('<B1-Motion>', self.onPanMotion)
        
        self.bind_all('<MouseWheel>', self.onZoon)

    def _draw_edge(self, u, v):
        """Draw edge(s).  u and v are from self.dataG"""

        # Find display nodes asoccoiated with these data nodes
        frm_disp = self._find_disp_node(u) 
        to_disp = self._find_disp_node(v)

        if isinstance(self.dataG, nx.MultiGraph):
            edges = self.dataG.edge[u][v]
        elif isinstance(self.dataG, nx.Graph):
            edges = {0: self.dataG.edge[u][v]}
        else:
            raise NotImplementedError('Data Graph Type not Supported')

        # Figure out edge arc distance multiplier
        if len(edges) == 1:
            m = 0
        else:
            m = 15

        for key, data in edges.items():
            token = self._EdgeTokenClass(data)
            self.dispG.add_edge(frm_disp, to_disp, key, {'dataG_id': (u,v),
                                                'dispG_frm': frm_disp,
                                                'token': token,
                                                'm': m})
            x1,y1 = self._node_center(frm_disp)
            x2,y2 = self._node_center(to_disp)
            xa,ya = self._spline_center(x1,y1,x2,y2,m)

            cfg = token.render()
            l = self.create_line(x1,y1,xa,ya,x2,y2, tags='edge', smooth=True, **cfg)
            self.dispG[frm_disp][to_disp][key]['token_id'] = l

            if m > 0:
                m = -m # Flip sides
            else:
                m = -(m+m)  # Go next increment out

    def _draw_node(self, coord, data_node):
        """Create a token for the data_node at the given coordinater"""
        (x,y) = coord
        data = self.dataG.node[data_node]
        token = self._NodeTokenClass(self, data, data_node)
        id = self.create_window(x, y, window=token, anchor=tk.CENTER,
                                  tags='node')
        self.dispG.add_node(id, {'dataG_id': data_node, 
                                 'token_id': id, 'token': token})
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
        
        if isinstance(node, list):
            neighbors = set(node)
        else:
            neighbors = set([node])
        for i in range(levels):
            for n in neighbors:
                neighbors = set(graph.neighbors(n)).union(neighbors)
        return graph.subgraph(neighbors)

    def _radial_behind(self, home_node, behind_node):
        """Detect what nodes create a radial string behind the edge from
        home_node to behind_node"""

        base_islands = nx.number_connected_components(self.dispG)

        # If we remove the edge in question, it should radialize the system
        #  and we can then detect the side to remove
        G = nx.Graph()
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
        x = event.x_root
        y = event.y_root   
        
        # Move everyone proportional to how far they are from the cursor
        ids = self.find_withtag('node') # + self.find_withtag('edge')
        
        for i in ids:
            ix, iy, t1, t2 = self.bbox(i)
            
            dx = (x-ix)*factor
            dy = (y-iy)*factor
            
            self.move(i, dx, dy)
            
        # Redraw all the edges
        for to_node, from_node, data in self.dispG.edges_iter(data=True):
            from_xy = self._node_center(from_node)
            to_xy = self._node_center(to_node)
            if data['dispG_frm'] != from_node:
                # Flip!
                a = from_xy[:]
                from_xy = to_xy[:]
                to_xy = a[:]
            spline_xy = self._spline_center(*from_xy+to_xy+(data['m'],))

            self.coords(data['token_id'], (from_xy+spline_xy+to_xy))
            
        

    def onNodeButtonPress(self, event):
        """Being drag of an object"""
        # record the item and its location
        item = self._get_id(event)
        self._drag_data["item"] = item
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

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
        for _, to_node, edge in self.dispG.edges_iter(from_node, data=True):
            to_xy = self._node_center(to_node)
            if edge['dispG_frm'] != from_node:
                # Flip!
                spline_xy = self._spline_center(*to_xy+from_xy+(edge['m'],))
                self.coords(edge['token_id'], (to_xy+spline_xy+from_xy))
            else:
                spline_xy = self._spline_center(*from_xy+to_xy+(edge['m'],))
                self.coords(edge['token_id'], (from_xy+spline_xy+to_xy))
    
    def onTokenRightClick(self, event):
        item = self._get_id(event)
        
        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Grow', command=lambda: self.grow_node(item), 
                              accelerator='G')
        popup.add_command(label='Mark', command=lambda: self.mark_node(item),
                              accelerator='M')
        popup.add_command(label='Hide', command=lambda: self.hide_node(item),
                              accelerator='H')
                              
        hide_behind = tk.Menu(popup, tearoff=0)
        for _, n in self.dispG.edges_iter(item):
            assert _ == item
            if self._radial_behind(item, n):
                state = tk.ACTIVE
            else:
                state = tk.DISABLED
            hide_behind.add_command(label=str(self.dispG.node[n]['dataG_id']), 
                  state=state, 
                  command=lambda item=item, n=n: self.hide_behind(item, n))
                
        popup.add_cascade(label='Hide Behind', menu=hide_behind)
        
            
        
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
    
        
    def grow_node(self, disp_node):
        data_node = self.dispG.node[disp_node]['dataG_id']
        existing_data_nodes = set([ v['dataG_id'] 
                                    for k,v in self.dispG.node.items() ])
        
        grow_graph = self._neighbors(data_node)
        
        # We also need grow_graph to include nodes which are already
        # ploted but are not immediate neighbors, so that we can successfully
        # capture their edges.  To do this, we should subgraph the data graph
        # using the nodes of the grow graph and existing data nodes
        nodes = set(grow_graph.nodes()).union(existing_data_nodes)
        grow_graph = self.dataG.subgraph(nodes)
        
        # Build layout considering existing nodes and 
        #  argument to center around the home node (ie, "disp_node")
        fixed = {}
        for n,d in self.dispG.nodes_iter(data=True):
            fixed[d['dataG_id']] = self.coords(n)

        layout = self.create_layout(grow_graph,
                                    pos=fixed, fixed=list(fixed.keys()))
        ##for k in list(layout.keys()):
        ##    layout[k] = [layout[k][0]*scale, layout[k][1]*scale]
        # Recenter around existing node
        (existx, existy) = self._node_center(disp_node)
        deltax = existx - layout[data_node][0]
        deltay = existy - layout[data_node][1]
        for k in list(layout.keys()):
            layout[k] = [layout[k][0]+deltax, layout[k][1]+deltay]
        
        
            
        # Filter the graph to only include new edges
        for n,m in grow_graph.copy().edges_iter():
            if (n in existing_data_nodes) and (m in existing_data_nodes):
                grow_graph.remove_edge(n,m)

        # Remove any nodes which connected to only existing nodes (ie, they
        #  they connect to nothing else in grow_graph)
        for n, degree in grow_graph.copy().degree_iter():
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
    
    def hide_node(self, disp_node):
        
        # Remove all the edges from display
        for n, m, d in self.dispG.edges_iter(disp_node, data=True):
            self.delete(d['token_id'])
        
        # Remove the node from display
        self.delete(disp_node)
        
        # Remove the node from dispG
        self.dispG.remove_node(disp_node)
        
        self._graph_changed()
    
    def mark_node(self, disp_node):
        """Mark a display node"""
        token = self.dispG.node[disp_node]['token']
        token.mark()

    def onEdgeRightClick(self, event):
        item = self._get_id(event, 'edge')
        for u,v,k,d in self.dispG.edges_iter(key=True, data=True):
            if d['token_id'] == item:
                break
        
        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Mark', command=lambda: self.mark_edge(u,v,k))
                              
        try:
            popup.post(event.x_root, event.y_root)
        finally:
            popup.grab_release()
        
    
    def hide_edge(self, edge_id):
        # This feature breaks the "grow" feature.  Also I've decided I kind of
        #  don't like it as it's decieving to have both nodes on the display
        #  but not be showing an edge between them
        raise NotImplementedError()
        for u, v, d in self.dispG.edges_iter(data=True):
            if d['token_id']==edge_id:
                self.dispG.remove_edge(u,v)
                break
        self.delete(edge_id)
        self._graph_changed()
    
    def mark_edge(self, disp_u, disp_v, key):
        token = self.dispG[disp_u][disp_v][key]['token']
        token_id = self.dispG[disp_u][disp_v][key]['token_id']
        
        cfg = token.mark()
        self.itemconfig(token_id, **cfg)

    
    def clear(self):
        """Clear the canvas and display graph"""
        self.delete(tk.ALL)
        self.dispG.clear()
    
    def plot(self, home_node, levels=1):
        """Plot node (from dataG) out to levels"""
        graph = self._neighbors(home_node, levels=levels)
        self._plot_graph(graph)
    
    def plot_path(self, frm_node, to_node, levels=1):
        """Plot shortest path between two nodes"""
        try:
            path = nx.shortest_path(self.dataG, frm_node, to_node)
        except nx.NetworkXNoPath as e:
            tkm.showerror("No path", str(e))
            return
        except nx.NetworkXError as e:
            tkm.showerror("Node not in graph", str(e))
            return
        
        graph = self.dataG.subgraph(self._neighbors(path,levels=levels))
        
        self.clear()
        self._plot_graph(graph)
        
        # Mark the path
        if levels > 0:
            for u, v in zip(path[:-1], path[1:]):
                u_disp = self._find_disp_node(u)
                v_disp = self._find_disp_node(v)
                for key, value in self.dispG.edge[u_disp][v_disp].items():
                    self.mark_edge(u_disp, v_disp, key)
        
        
        
    def _plot_graph(self, graph):
        # Create nodes
        scale = min(self.winfo_width(), self.winfo_height())
        if scale == 1:
            # Canvas not initilized yet; use height and width hints
            scale = int(min(self['width'], self['height']))
            
        scale -= 50
        if len(graph) > 1:
            layout = self.create_layout(graph, scale=scale)
            for n in graph.nodes():
                self._draw_node(layout[n]+20, n)
        else:
            self._draw_node((scale/2, scale/2), graph.nodes()[0])

        # Create edges
        for frm, to in set(graph.edges()):
            self._draw_edge(frm, to)
        
        self._graph_changed()
        
        
        
    def _graph_changed(self):
        """Handle token callbacks
        Called every time a node or edge has been added or removed from
        the display graph.  Used to propagate completeness indicators
        down to the node's tokens"""
        
        for n, d in self.dispG.nodes_iter(data=True):
            token = d['token']
            if self.dispG.degree(n) == self.dataG.degree(d['dataG_id']):                
                token.mark_complete()
            else:
                token.mark_incomplete()
            
        
    def _find_disp_node(self, data_node):
        """Given a node's name in self.dataG, find in self.dispG"""
        disp_node = [a for a, d in self.dispG.nodes_iter(data=True) 
                    if d['dataG_id'] == data_node]
        if len(disp_node) == 0:
            raise ValueError("Data Node '%s' is not currently displayed"%\
                                data_node)
        elif len(disp_node) != 1:
            raise AssertionError("Data node '%s' is displayed multiple "
                                    "times" % data_node)
        return disp_node[0]

#    def create_layout(self, G, pos=None, fixed=None, scale=1.0):
#        return nx.spring_layout(G, scale=scale)

    def create_layout(self, G, pos=None, fixed=None, scale=1.0):
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
        k=(min(self.winfo_width(), self.winfo_height())*.66)/np.sqrt(nnodes)

        # Alternate k, for when vieweing the whole graph, not a subset
        #k=dom_size/np.sqrt(nnodes)
        pos=self._fruchterman_reingold(A,dim,k,pos_arr,fixed)
        
        if fixed is None:
            # Only rescale non fixed layouts
            pos= nx.layout._rescale_layout(pos,scale=scale)

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
    
        if pos==None:
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

def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el









