import networkx as nx
from networkx_viewer import Viewer

### Example 1 ####
G = nx.MultiGraph()
G.add_edge('a',2)
G.add_edge(2,'c')
G.add_edge('a','c',0,{'dash':(2,2)})
G.add_edge('a','c',1)
G.add_edge('a',4)
G.add_edge(4,'c')
G.add_edge('out','c',0,{'fill':'red', 'width':3})
G.add_edge('c','d')
G.add_edge('d',2)
# Growth edges
G.add_edge('out',11)
G.add_edge('out',12,0)
G.add_edge('out',12,1)
G.add_edge('out',12,2)
G.add_edge('out',12,3)
G.add_edge(12, 'd')
G.add_edge('TTTTT',11)
G.add_edge('qqqq', 'TTTTT')
G.add_edge('alone','alone')

# Some example TkPassthrough options
G.node['a']['fill'] = 'white'
G.node['a']['dash'] = (2,2)
G.node[2]['label_fill'] = 'blue'
G.node[2]['label_text'] = 'LOOOOOONG'
app = Viewer(G, home_node='a', levels=2)
#app = GraphViewerApp(G, home_node='a', levels=2)
app.mainloop()

### Example 2 ###
G = nx.Graph()
G.add_edge('a','b')
G.add_edge('b','c')
G.add_edge('c','a',{'fill':'green'})
G.add_edge('c','d')
G.node['a']['outline'] = 'blue'
G.node['d']['label_fill'] = 'red'

app = Viewer(G)
app.mainloop()