import unittest
import mock
import networkx as nx

try:
    import networkx_viewer as nxv
except ImportError:
    import __init__ as nxv

@mock.patch('tkMessageBox.showerror', lambda x=None,y=None: None)
class TestGraphCanvas(unittest.TestCase):
    def setUp(self):
        # Create the graph for testing
        G = nx.Graph()
        G.add_edge('a',2)
        G.add_edge(2,'c')
        G.add_edge('a','c')
        G.add_edge('a',4)
        G.add_edge(4,'c')
        G.add_edge('out','c')
        G.add_edge('c','d')
        G.add_edge('d',2)
        # Growth edges
        G.add_edge('out',11)
        G.add_edge('out',12)
        G.add_edge(12, 'd')
        G.add_edge('TTTTT',11)
        G.add_edge('qqqq', 'TTTTT')
        G.add_edge('alone','alone')
        self.input_G = G.copy()

        # Viewer under test
        self.a = nxv.GraphCanvas(G)

    def check_subgraph(self):
        """Verify that display graph is a subgraph of input"""
        dispG = self.a.dispG
        displayed_nodes = [d['dataG_id'] for n,d in dispG.nodes_iter(data=True)]
        subdataG = self.input_G.subgraph(displayed_nodes)

        self.assertEqual(len(dispG), len(subdataG))

        for disp_node, data in dispG.nodes_iter(data=True):
            data_node = data['dataG_id']
            # Make sure we're displaying all edges for all displayed nodes
            disp_deg = dispG.degree(disp_node)
            subdata_deg = subdataG.degree(data_node)
            data_deg = self.input_G.degree(data_node)
            token = data['token']
            self.assertEqual(disp_deg, subdata_deg,
              "Inconsistent edges for dataG:%s ; dispG:%s" %(data_node, disp_node))

            # If a node does not have all its edges drawn because the opposite
            #  node is hidden, make sure we have it marked as "incomplete"
            if disp_deg == data_deg:
                self.assertEqual(token._complete, True)
            elif disp_deg < data_deg:
                self.assertEqual(token._complete, False)
            else:
                self.fail("Display graph has more edges than data graph?")

    def check_num_nodes_edges(self, number_of_nodes, number_of_edges):
        self.assertEqual(len(self.a.dispG), number_of_nodes)
        self.assertEqual(len(self.a.dispG.edges()), number_of_edges)

    def display_a(self):
        """Change the canvas to show 2 levels away form node 'a'
        This is kind of my standard testing position"""
        self.a.clear()
        self.a.plot(home_node='a', levels=2)

    def test_full_graph(self):
        self.check_subgraph()

        for disp_node, disp_data in self.a.dispG.nodes_iter(data=True):
            token = disp_data['token']
            self.assertEqual(token._complete, True)

    def test_partial_graph(self):
        self.display_a()
        self.check_subgraph()
        self.assertEqual(len(self.a.dispG), 6)
        self.check_num_nodes_edges(6, 8)

        self.a.clear()
        self.a.plot(home_node=11, levels=1)
        self.check_subgraph()
        self.check_num_nodes_edges(3, 2)

    def test_alone(self):
        self.a.clear()
        self.a.plot('alone')

        self.check_subgraph()
        self.check_num_nodes_edges(1,1)

    def test_grow(self):
        self.display_a()
        out = self.a._find_disp_node('out')

        self.a.grow_node(out)
        self.check_subgraph()

        self.check_num_nodes_edges(8, 11)

    def test_hide(self):
        self.display_a()
        out = self.a._find_disp_node('c')

        self.a.hide_node(out)
        self.check_subgraph()

        self.check_num_nodes_edges(5, 3)

    def test_hide_behind(self):
        # Center the graph around node "out"
        self.a.clear()
        self.a.plot(home_node='out', levels=2)

        home = self.a._find_disp_node('out')
        behind = self.a._find_disp_node(11)

        self.a.hide_behind(home, behind)
        self.check_subgraph()

        self.check_num_nodes_edges(7, 10)

    def test_hide_behind_error(self):
        # We can't hind behind a non-radial set
        home = self.a._find_disp_node('a')
        behind = self.a._find_disp_node('c')

        with self.assertRaises(ValueError):
            self.a.hide_behind(home, behind)

    def test_plot_path(self):
        self.a.plot_path('a', 'out', levels=0)
        self.check_subgraph()

        self.check_num_nodes_edges(3, 2)

        #########
        self.a.plot_path('a', 'out', levels=1)
        self.check_subgraph()

        self.check_num_nodes_edges(8, 11)

        #########
        self.a.plot_path('a', 'out', levels=2)
        self.check_subgraph()

        self.check_num_nodes_edges(9, 12)

    def test_plot_path_error_no_node(self):
        self.a.clear()
        self.a.plot_path('a','bad')

        self.check_num_nodes_edges(0, 0)

    def test_plot_path_error_no_path(self):
        self.a.clear()
        self.a.plot_path('a','alone')

        self.check_num_nodes_edges(0, 0)

    def test_mark_node(self):
        a = self.a._find_disp_node('a')
        token = self.a.dispG.node[a]['token']
        self.a.mark_node(a)
        self.assertEqual(token._marked, True)
        self.assertEqual(token['background'], 'yellow')

        # Unmark
        self.a.mark_node(a)
        self.assertEqual(token._marked, False)
        self.assertEqual(token['background'], token._default_bg)

    def test_mark_edge(self):
        c = self.a._find_disp_node('c')
        out = self.a._find_disp_node('out')

        token = self.a.dispG.edge[c][out]['token']
        self.a.mark_edge(c, out)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out]['token_id'])
        self.assertEqual(token._marked, True)
        self.assertEqual(cfg['width'][-1], '4.0')

        # Unmark
        self.a.mark_edge(c, out)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out]['token_id'])
        self.assertEqual(token._marked, False)
        self.assertEqual(cfg['width'][-1], '1.0')


class TestGraphCanvasTkPassthrough(TestGraphCanvas):
    # We inherit for the base tester to make sure we continue to
    #  provide at least that level of functionality

    def setUp(self):
        # Create graph same as basic GraphCanvas
        super(TestGraphCanvasTkPassthrough, self).setUp()

        # Add some attributes to the dictionary to pass through to tk
        G = self.input_G.copy()
        G.node['a']['fill'] = 'white'
        G.node['a']['dash'] = (2,2)
        G.node[2]['label_fill'] = 'blue'
        G.node[2]['label_text'] = 'LOOOOOONG'
        G.edge['a']['c']['dash'] = (2,2)
        G.edge['out']['c']['fill'] = 'red'
        G.edge['out']['c']['width'] = 3

        self.input_G = G.copy()

        # Viewer under test
        self.a = nxv.GraphCanvas(G,
                    EdgeTokenClass=nxv.TkPassthroughEdgeToken,
                    NodeTokenClass=nxv.TkPassthroughNodeToken)

    @classmethod
    def setUpClass(cls):
        # Because edge out-c has a native width, we expect it to fail
        #  the base test_mark_edge. The test_mark_edge_pass case has been
        #  developed to test correct functionality
        cls.test_mark_edge = unittest.expectedFailure(cls.test_mark_edge)

    def test_mark_edge_pass(self):
        c = self.a._find_disp_node('c')
        out = self.a._find_disp_node('out')

        token = self.a.dispG.edge[c][out]['token']

        self.a.mark_edge(c, out)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out]['token_id'])
        self.assertEqual(token._marked, True)
        self.assertEqual(cfg['width'][-1], '4.0')

        # Unmark
        self.a.mark_edge(c, out)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out]['token_id'])
        self.assertEqual(token._marked, False)
        self.assertEqual(cfg['width'][-1], '3.0')

    def test_node_passthrough(self):
        node = self.a._find_disp_node('a')
        token = self.a.dispG.node[node]['token']
        cfg = token.itemconfig(token.marker)

        self.assertEqual(cfg['fill'][-1], 'white')
        self.assertEqual(cfg['dash'][-1], ('2','2'))

    def test_node_label_passthrough(self):
        node = self.a._find_disp_node(2)
        token = self.a.dispG.node[node]['token']
        cfg = token.itemconfig(token.label)

        self.assertEqual(cfg['fill'][-1], 'blue')
        self.assertEqual(cfg['text'][-1], 'LOOOOOONG')

    def test_edge_passthrough(self):
        a = self.a._find_disp_node('a')
        c = self.a._find_disp_node('c')
        out = self.a._find_disp_node('out')

        # Test edge a-c
        token = self.a.dispG.edge[a][c]['token']
        token_id = self.a.dispG.edge[a][c]['token_id']
        cfg = self.a.itemconfig(token_id)

        self.assertEqual(cfg['dash'][-1], ('2','2'))

        # Test edge out-c
        token = self.a.dispG.edge[out][c]['token']
        token_id = self.a.dispG.edge[out][c]['token_id']
        cfg = self.a.itemconfig(token_id)

        self.assertEqual(cfg['fill'][-1], 'red')
        self.assertEqual(cfg['width'][-1], '3.0')

if __name__ == '__main__':
    unittest.main()
