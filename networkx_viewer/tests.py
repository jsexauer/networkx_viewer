import unittest
from mock import patch
import networkx as nx

try:
    import networkx_viewer as nxv
except ImportError:
    from . import __init__ as nxv

import sys

if sys.version_info > (3, 0):
    # Python 3 patching
    SHOWERROR_FUNC = 'tkinter.messagebox.showerror'
    ASKYESNO_FUNC = 'tkinter.messagebox.askyesno'
else:
    # Python 2
    SHOWERROR_FUNC = 'tkMessageBox.showerror'
    ASKYESNO_FUNC = 'tkMessageBox.askyesno'


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
        G.add_node('alone')
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
                self.assertEqual(token.is_complete, True)
            elif disp_deg < data_deg:
                self.assertEqual(token.is_complete, False)
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
            self.assertEqual(token.is_complete, True)

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
        self.check_num_nodes_edges(1,0)

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
        with patch(SHOWERROR_FUNC) as errorMsgBox:
            self.a.plot_path('a','bad')

        self.check_num_nodes_edges(0, 0)
        self.assertTrue(errorMsgBox.called)

    def test_plot_path_error_no_path(self):
        self.a.clear()
        with patch(SHOWERROR_FUNC) as errorMsgBox:
            self.a.plot_path('a','alone')

        self.check_num_nodes_edges(0, 0)
        self.assertTrue(errorMsgBox.called)

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

        token = self.a.dispG.edge[c][out][0]['token']
        self.a.mark_edge(c, out, 0)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out][0]['token_id'])
        self.assertEqual(token._marked, True)
        self.assertEqual(cfg['width'][-1], '4.0')

        # Unmark
        self.a.mark_edge(c, out, 0)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out][0]['token_id'])
        self.assertEqual(token._marked, False)
        self.assertEqual(cfg['width'][-1], '1.0')

    def test_plot_list(self):
        self.a.clear()
        self.a.plot(['a','c','d'])
        self.check_subgraph()
        displayed = [d['dataG_id'] for n,d in self.a.dispG.nodes(data=True)]

        for k in['a','c','d']:
            self.assertIn(k, displayed)

    def test_add_to_plot_with_path(self):
        # Test adding nodes around qqqq to a display showing nodes around a
        self.display_a()

        with patch(ASKYESNO_FUNC) as prompt:
            prompt.return_value = True      # Yes, we want to include path
            self.a.plot_additional(set(['qqqq']), levels=1)

        self.assertTrue(prompt.called)
        self.check_subgraph()
        self.check_num_nodes_edges(9, 11)
        # All connected together
        self.assertEqual(nx.number_connected_components(self.a.dispG), 1)

    def test_add_to_plot_without_path(self):
        # Test adding nodes around qqqq to a display but as an island
        self.display_a()

        with patch(ASKYESNO_FUNC) as prompt:
            prompt.return_value = False      # No, we don't want to include path
            self.a.plot_additional(set(['qqqq']), levels=1)

        self.assertTrue(prompt.called)
        self.check_subgraph()
        self.check_num_nodes_edges(8, 9)
        # There are two islands
        self.assertEqual(nx.number_connected_components(self.a.dispG), 2)

    def test_add_to_plot_without_path2(self):
        # Test adding nodes around qqqq but because our levels is so big, we
        #  should just connect to the existing graph (no prompt)
        self.display_a()

        with patch(ASKYESNO_FUNC) as prompt:
            self.a.plot_additional(set(['qqqq']), levels=2)

        self.assertFalse(prompt.called) # We should not prompt
        self.check_subgraph()
        self.check_num_nodes_edges(9, 11)
        # All connected together
        self.assertEqual(nx.number_connected_components(self.a.dispG), 1)

    def test_replot_keep_marked(self):
        # Make sure the marked status of a node and edge is maintained
        #  through a replot
        c = self.a._find_disp_node('c')
        out = self.a._find_disp_node('out')

        # Mark edge c-out and node out
        c_token = self.a.dispG.node[c]['token']
        out_token = self.a.dispG.node[out]['token']
        edge_token = self.a.dispG.edge[c][out][0]['token']
        self.a.mark_edge(c, out, 0)
        self.a.mark_node(out)
        self.assertEqual(edge_token.is_marked, True)
        self.assertEqual(c_token.is_marked, False)
        self.assertEqual(out_token.is_marked, True)

        # Replot
        self.a.replot()

        # Ensure markings still hold
        c = self.a._find_disp_node('c')
        out = self.a._find_disp_node('out')
        c_token = self.a.dispG.node[c]['token']
        out_token = self.a.dispG.node[out]['token']
        edge_token = self.a.dispG.edge[c][out][0]['token']
        self.assertEqual(edge_token.is_marked, True)
        self.assertEqual(c_token.is_marked, False)
        self.assertEqual(out_token.is_marked, True)


class TestGraphCanvasFiltered(TestGraphCanvas):
    def setUp(self):
        super(TestGraphCanvasFiltered, self).setUp()
        # Modify graph to include a "real" on all existing nodes which
        # evaluates to True when we we will filter by them
        G = self.a.dataG

        for n in G.nodes_iter():
            G.node[n]['real'] = True

        # Now we're going to add a couple of "fake" nodes; IE, nodes
        #  that should be not be displayed because they are not in the filter.
        #  If they do show up, they'll cause us to fail some of the base checks
        G.add_edge('out','fake1')
        G.add_edge('a','fake2')
        G.add_edge('qqqq','fake3')
        G.add_edge('fake3','fake4')
        G.add_node('fake_alone')

        # Viewer under test
        self.a = nxv.GraphCanvas(G)
        self.input_G = G
        #gself.filter_lambda = "not str(u).startswith('fake')"
        self.filter_lambda = "d.get('real',False)"
        self.a.add_filter(self.filter_lambda)

    def test_full_graph(self):
        # Redefine this test, as when filtered, not all tokens will be marked
        # complete
        self.check_subgraph()

        for disp_node, disp_data in self.a.dispG.nodes_iter(data=True):
            token = disp_data['token']
            dataG_id = disp_data['dataG_id']
            if dataG_id in ('out','a','qqqq'):
                # Has a "fake" node attached
                self.assertEqual(token.is_complete, False)
            else:
                self.assertEqual(token.is_complete, True)

    #### NEW TESTS ####
    def test_find_disp_node(self):
        # Make sure _find_disp_node raises a NodeFiltered exception
        from networkx_viewer.graph_canvas import NodeFiltered
        with self.assertRaises(NodeFiltered):
            self.a._find_disp_node('fake1')

    def test_bad_filter_lambda(self):
        # Caues error because filter_lambda has a syntax error
        filter_lambda = "d.get('real', False"   # Missing closing )
        self.display_a()

        self.check_num_nodes_edges(6, 8)
        with patch(SHOWERROR_FUNC) as errorMsgBox:
            self.a.add_filter(filter_lambda)
        self.assertTrue(errorMsgBox.called)
        # Make sure no edges added or removed
        self.check_num_nodes_edges(6, 8)

    def test_bad_filter_lambda2(self):
        # Causes error because not every d has the attribute "real"
        # but error only shows on grow
        filter_lambda = "d['real']"
        self.display_a()
        self.a.remove_filter(self.filter_lambda)

        self.check_num_nodes_edges(6, 8)
        with patch(SHOWERROR_FUNC) as errorMsgBox:
            self.a.add_filter(filter_lambda)
            self.assertFalse(errorMsgBox.called)
        with patch(SHOWERROR_FUNC) as errorMsgBox:
            try:
                self.a.grow_node(self.a._find_disp_node('out'))
            except Exception:
                pass
        self.assertTrue(errorMsgBox.called)
        # Make sure no edges added or removed
        #self.check_num_nodes_edges(6, 8)


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

        token = self.a.dispG.edge[c][out][0]['token']

        self.a.mark_edge(c, out, 0)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out][0]['token_id'])
        self.assertEqual(token._marked, True)
        self.assertEqual(cfg['width'][-1], '4.0')

        # Unmark
        self.a.mark_edge(c, out, 0)
        cfg = self.a.itemconfig(self.a.dispG.edge[c][out][0]['token_id'])
        self.assertEqual(token._marked, False)
        self.assertEqual(cfg['width'][-1], '3.0')

    def test_node_passthrough(self):
        node = self.a._find_disp_node('a')
        token = self.a.dispG.node[node]['token']
        cfg = token.itemconfig(token.marker)

        self.assertEqual(cfg['fill'][-1], 'white')
        chk = (cfg['dash'][-1] == ('2','2')) or (cfg['dash'][-1] == ('2 2'))
        self.assert_(chk)

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
        token = self.a.dispG.edge[a][c][0]['token']
        token_id = self.a.dispG.edge[a][c][0]['token_id']
        cfg = self.a.itemconfig(token_id)

        chk = (cfg['dash'][-1] == ('2','2')) or (cfg['dash'][-1] == ('2 2'))
        self.assert_(chk)

        # Test edge out-c
        token = self.a.dispG.edge[out][c][0]['token']
        token_id = self.a.dispG.edge[out][c][0]['token_id']
        cfg = self.a.itemconfig(token_id)

        self.assertEqual(cfg['fill'][-1], 'red')
        self.assertEqual(cfg['width'][-1], '3.0')

    def test_refresh(self):
        # Make sure that if we change the underlying data dictionaries of the
        #  dataG and call refresh, the changes propagate

        # Make edge a-c magenta
        self.a.dataG.edge['a']['c']['fill'] = 'magenta'

        # Make node a magenta
        self.a.dataG.node['a']['fill'] = 'magenta'

        self.a.refresh()

        # See that the changes propagated through
        a = self.a._find_disp_node('a')
        c = self.a._find_disp_node('c')

        token_id = self.a.dispG.edge[a][c][0]['token_id']
        cfg = self.a.itemconfig(token_id)
        self.assertEqual(cfg['fill'][-1], 'magenta')

        token = self.a.dispG.node[a]['token']
        cfg = token.itemconfig(token.marker)
        self.assertEqual(cfg['fill'][-1], 'magenta')

class TestGraphCanvasMultiGraph(TestGraphCanvas):
    def setUp(self):
        super(TestGraphCanvasMultiGraph, self).setUp()

        # Add in some extra edges
        G = nx.MultiGraph(self.input_G)
        G.add_edge('a','c')

        G.add_edge('out',12)
        G.add_edge('out',12)
        G.add_edge('out',12)
        self.input_G = G.copy()

        # Viewer under test
        self.a = nxv.GraphCanvas(G)

    def check_num_nodes_edges(self, number_of_nodes, number_of_edges):
        # If we're currently displaying any of the node-pairs with
        #  multiple edges, we'll need to add the number of edges observed

        try:
            self.a._find_disp_node('a')
            self.a._find_disp_node('c')
        except ValueError:
            # Edge a-c not displayed
            pass
        else:
            # Edge a-c dispayed.  We added 1 edge in self.setUp
            number_of_edges += 1

        try:
            self.a._find_disp_node('out')
            self.a._find_disp_node(12)
        except ValueError:
            # Edge out-12 not displayed
            pass
        else:
            # Edge out-12 dispayed.  We added 3 edges in self.setUp
            number_of_edges += 3


        return super(TestGraphCanvasMultiGraph,
                self).check_num_nodes_edges(number_of_nodes, number_of_edges)


if __name__ == '__main__':
    unittest.main()
