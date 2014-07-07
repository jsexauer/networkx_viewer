NetworkX Viewer
================

![Build Status](https://travis-ci.org/jsexauer/networkx_viewer.svg?branch=master)

Introduction
------------

NetworkX Viewer provides a basic interactive GUI to view
[networkx](https://networkx.github.io/) graphs.  In addition to standard
plotting and layout features as found natively in networkx, the GUI allows
you to:

  - Drag nodes around to tune the default layout
  - Show and hide nodes
  - Pan and zoom
  - Display nodes only within a certain number of hops ("levels") of
    a "home node"
  - Display and highlight the shortest path between two nodes.  Nodes
    around the path can also be displayed within a settable number of
    levels
  - Use attributes stored in the graph's node and edge dictionaries to
    customize the appearance of the node and edge tokens in the GUI
  - Mark nodes and edges for reference

A typical usage would be:
```python
import networkx as nx
from networkx_viewer import Viewer

G = nx.Graph()
G.add_edge('a','b')
G.add_edge('b','c')
G.add_edge('c','a',{'fill':'green'})
G.add_edge('c','d')
G.node['a']['outline'] = 'blue'
G.node['d']['label_fill'] = 'red'

app = Viewer(G)
app.mainloop()
```

The result will be:

![NetworkX Viewer Window](http://s8.postimg.org/k130sbsut/networkx_viewer.png)

Using the GUI
-------------
The default layout for the nodes is to use `nx.spring_layout`.  While this
layout is pretty good, it is not perfect.  The GUI supports standard features
like rearanging the nodes, panning, and zooming.

By default, the viewer will display the entire graph on initialization.
However, most of the power in the GUI comes in showing a subset of the graph.
You can specify a subgraph to display using:
```python
app = Viewer(G, home_node='a', levels=1)
```

Several actions can be taken by right-clicking on nodes and edges, including
  - *Grow:* Display all nodes connected to this node that may not be
    currently displayed.  A node which does not have all of its neighbors
    currently displayed will have a grey label.
  - *Hide*
  - *Hide Behind:* Hide radial sections of the graph that are behind the edge
    formed by the node the cursor is currently over and the node in the menu.
    Note: if the graph is not radial behind the selected node, this item is
    greyed out in the dropdown.

You can also simply hover over a node and press the shortcut key ("G" for
grow, "H" for hide, etc...) to activate the action.

At the bottom of the screen is a box to enter a node to graph
just that node.  If you wish to plot the shortest path between two nodes, enter
their names in the two boxes.  The Levels box indicates how many levels away
from the node(s) to display.

Using the Tk Pass-through
-------------------------
If the data dictionary stored in the graph for an edge or node contains a key
that can be used by Tk, the token will be customized as such.  Specifcially,

  - If a node contains a key used to configure
    [Tkinter.Canvas.create_oval][1], it will be used to customize the node's
    marker (ie, the red circle).
  - If a node contains a key prefixed with "label_" (for example, "label_font"
    or "label_fill") that can be used to configure
    [Tkinter.Canvas.create_text][2], it will be used to customize the node's
    label.
  - If an edge contains a key which can be used by
    [Tkinter.Canvas.create_line][3], it will be used to customize the edge's
    display properties.

[1]: http://effbot.org/tkinterbook/canvas.htm#Tkinter.Canvas.create_oval-method
[2]: http://effbot.org/tkinterbook/canvas.htm#Tkinter.Canvas.create_text-method
[3]: http://effbot.org/tkinterbook/canvas.htm#Tkinter.Canvas.create_line-method

Expanding and Customizing the GUI
---------------------------------
The core Tk widget that is implemented by networkx_viewer is the `GraphCanvas`
widget.  If you simply wish to use the GUI as presented as part of a larger
application, you can just instantiate the canvas, passing it the graph to
display as an argument and pack or grid it into your Tk application like any
other canvas widget.

If you wish to change the tokens used for edges or nodes, subclass `NodeToken`
or `EdgeToken` and pass as an argument into the GraphCanvas as such.  For
example:

```python
import Tkinter as tk
import networkx as nx
from networkx_viewer import NodeToken, GraphCanvas

class CustomNodeToken(NodeToken):
    def render(self, data, node_name):
        """Example of custom Node Token
        Draw a circle if the node's data says we are a circle, otherwise
        draw us as a rectangle.  Also, if data contains a color key,
        use that as our color (default, red)
        """
        # For our convenience, the render method is called with the
        #  graph's data attributes and the name of the node in the graph

        # Note that NodeToken is a subclass of Tkinter.Canvas, so we
        #  simply draw on ourselves to create the apperance for the node.

        # Make us 50 pixles big
        self.config(width=50, height=50)

        # Set color and other options
        marker_options = {'fill':       data.get('color','red'),
                          'outline':    'black'}

        # Draw circle or square, depending on what the node said to do
        if data.get('circle', None):
            self.create_oval(0,0,50,50, **marker_options)
        else:
            self.create_rectangle(0,0,50,50, **marker_options)

class ExampleApp(tk.Tk):
    def __init__(self, graph, **kwargs):
        tk.Tk.__init__(self)

        self.canvas = GraphCanvas(graph, NodeTokenClass=CustomNodeToken,
            **kwargs)
        self.canvas.grid(row=0, column=0, sticky='NESW')

G = nx.path_graph(5)
G.node[2]['circle'] = True
G.node[3]['color'] = 'blue'

app = ExampleApp(G)
app.mainloop()

```

Development Status
==================
As of July 2014, networkx_viewer is under active development.  Bugs or feature
requests should be submitted to the
[github issue tracker](https://github.com/jsexauer/networkx_viewer/issues).

