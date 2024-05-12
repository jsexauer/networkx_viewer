import networkx as nx
from networkx_viewer import Viewer


### Bug report ###
G = nx.DiGraph()
edges = [('paper_9912286', 'paper_9806074'), ('paper_9912286', 'paper_9810068'), ('paper_9912286', 'paper_9901023'), ('paper_9912286', 'paper_9808140'), ('paper_1001', 'paper_9308122'), ('paper_1001', 'paper_9304045'), ('paper_1001', 'paper_9912286')]
for e in edges:
    G.add_edge(*e)
app = Viewer(G)
app.mainloop()



### Example 1 ####
G = nx.MultiGraph()
G.add_edge('a',2)
G.add_edge(2,'c')
G.add_edge('a','c',0,dash=(2,2))
G.add_edge('a','c',1)
G.add_edge('a',4)
G.add_edge(4,'c')
G.add_edge('out','c',0, fill='red', width=3)
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
G.nodes['a']['fill'] = 'white'
G.nodes['a']['dash'] = (2,2)
G.nodes[2]['label_fill'] = 'blue'
G.nodes[2]['label_text'] = 'LOOOOOONG'

### Filter example
for n in G.nodes():
    G.nodes[n]['real'] = True

# Now we're going to add a couple of "fake" nodes; IE, nodes
#  that should be not be displayed because they are not in the filter.
#  If they do show up, they'll cause us to fail some of the base checks
G.add_edge('out','fake1')
G.add_edge('a','fake2')
G.add_edge('qqqq','fake3')
G.add_edge('fake3','fake4')
G.add_node('fake_alone')
###

app = Viewer(G, home_node='a', levels=2)
#app = GraphViewerApp(G, home_node='a', levels=2)
app.mainloop()

### Example 2 ###
G = nx.MultiGraph()
G.add_edge('a','b')
G.add_edge('b','c')
G.add_edge('c','a',0,**{'fill':'green'})
G.add_edge('c','d')
G.add_edge('c','d',1,**{'dash':(2,2)})
G.nodes['a']['outline'] = 'blue'
G.nodes['d']['label_fill'] = 'red'

app = Viewer(G)
app.mainloop()

### Example 3 ###
G = nx.MultiDiGraph()
G.add_edge('Arg2','Arg1')
G.add_edge('Arg3','Arg1',0)
G.add_edge('Arg3','Arg1',1)
G.add_edge('Arg4','Arg2')
G.add_edge('Arg5','Arg2')
G.add_edge('Arg6','Arg3')
G.nodes['Arg2']['outline'] = 'blue'
G.nodes['Arg1']['label_fill'] = 'red'
app = Viewer(G)
app.mainloop()