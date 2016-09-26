"""
Tests for the various nodes, handlers and typeclasses in the aisystem package.

In order to run these tests, you must add the aisystem package as an app
to your game's server/conf/settings.py file. See the README.md file for
information on how to do that.
"""

from unittest import TestCase
from django.conf import settings
from evennia import create_object, create_script, DefaultRoom
from evennia.utils.dbserialize import _SaverList, _SaverDict
from evennia.contrib.aisystem.typeclasses import (BehaviorTree, AIObject, 
    AIScript)
from evennia.contrib.aisystem.nodes import (SUCCESS, FAILURE, RUNNING, ERROR,
    RootNode, CompositeNode, DecoratorNode, LeafNode, Condition, Command,
    Transition, EchoLeaf, Selector, Sequence, MemSelector, MemSequence,
    ProbSelector,ProbSequence, Parallel, Verifier, Inverter, Succeeder, Failer,
    Repeater, Limiter, Allocator, EchoDecorator)


class TestTransition(TestCase):
    """
    Tests the add, shift, swap and interpose methods of the behavior tree class, as
    well as all methods associated with them.
    """

    def setUp(self):
        self.tree1 = create_script(BehaviorTree, key="tree1")
        self.tree2 = create_script(BehaviorTree, key="tree2")
        self.tree3 = create_script(BehaviorTree, key="tree3")

    def tearDown(self):
        pass

    def test_root_exists(self):
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        assert(isinstance(root1, RootNode))
        assert(isinstance(root2, RootNode))

    def test_node_str(self):
        """
        Test that the __str__ method of a given node returns the node's name.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        leaf = LeafNode("leaf", self.tree1, root1)
        s = str(leaf)
        assert(s == "leaf")

    def test_node_unicode(self):
        """
        Test that the __unicode__ method of a given node returns the node's
        name in unicode format.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        leaf = LeafNode("leaf", self.tree1, root1)
        s = unicode(leaf)
        assert(s == u"leaf")

    def test_add_and_remove_node(self):
        """
        Test the operation of adding, removing and then copying in the
        same node to/from the root node of a tree.

        Check that a newly created leaf node correctly inserts itself
        in its tree's hash dict, that it updates its parent correctly
        when added to the root node, and that it is removed correctly
        from its parent's children and its  via the tree's remove() method.
        Also check that re-adding it 
        """
        root1 = self.tree1.nodes[self.tree1.root]

        leafnode = LeafNode("Leaf node", self.tree1, root1)
        # check that the node is added to the tree's nodes registry
        assert(leafnode.hash in self.tree1.nodes.keys())
        assert(self.tree1.nodes[leafnode.hash] == leafnode)
        # check that the parent-child relationship is established
        assert(isinstance(root1.children, LeafNode))
        assert(root1.children.parent == root1)
        # check that there are only two nodes registered in the tree
        assert(len(self.tree1.nodes.keys()) == 2)

        err = self.tree1.remove(root1.children)
        assert(not err)

        # check that the node is removed from the tree's nodes registry
        assert(leafnode.hash not in self.tree1.nodes.keys())
        # check that the parent-child relationship is erased
        assert(root1.children == None)
        assert(leafnode.parent == None)
        # check that there is only one node registered in the tree
        assert(len(self.tree1.nodes.keys()) == 1)

        # test the add method of BehaviorTreeDB, copying in a new leaf node
        err = self.tree1.add(leafnode, root1)
        assert(not err)

        # check that the copied node is in the tree's nodes registry
        assert(leafnode.hash in self.tree1.nodes.keys())
        assert(isinstance(self.tree1.nodes[leafnode.hash], LeafNode))
        # check that the parent-child relationship is established
        assert(isinstance(root1.children, LeafNode))
        assert(root1.children.parent == root1)
        # check that there are only two nodes registered in the tree
        assert(len(self.tree1.nodes.keys()) == 2)

    def test_add_and_remove_from_composite(self):
        """
        Test the operations of adding three leaf nodes to a composite node,
        adding more leaf nodes to the composite node at the end of its
        children list and at a specific position in its children list,
        and moving one of its children to another position in its children
        list.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite = CompositeNode("composite node", self.tree1, 
            root1)
        leaf1 = LeafNode("leaf 1", self.tree1, composite)
        leaf2 = LeafNode("leaf 2", self.tree1, composite)
        leaf3 = LeafNode("leaf 3", self.tree1, composite)

        # check that all leaf nodes have been inserted
        assert(len(composite.children) == 3)
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)
        assert(composite.children[2] == leaf3)        

        err = self.tree1.add(leaf1, composite, position=2, copying=True)
        assert(not err)
        err = self.tree1.add(leaf1, composite, position=None, copying=True)
        assert(not err)
        # check that leaf3 is now the 4th node, and new leaf1
        # nodes are in the 3rd and 5th positions
        assert(composite.children[2].name == "leaf 1")
        assert(composite.children[3] == leaf3)
        assert(composite.children[2].name == "leaf 1")

        err = self.tree1.add(leaf1, composite, position=None, copying=False)
        assert(not err)
        # check that leaf1 has moved away from position 0
        assert(composite.children[0] != leaf1)
        # check that leaf1 has moved to the end-position
        assert(composite.children[-1] == leaf1)
        # check that there are still only 7 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 7)

    def test_recursive_add_hash(self):
        """
        Test whether recursive_add_hash works recursively by copying
        a subtree of one composite node and its two child leaf nodes
        to the composite's node own parent composite node, as well as
        copying another subtree from a different tree. This other subtree
        is composed of a composite node with a leaf node and a second
        composite node as children; the second composite node has two
        leaf nodes of its own.

        In the former case, identical hashes are detected in the registry
        and new hashes are assigned to the new nodes to avoid duplicates.
        In the latter case, the same hashes as those in tree2 are unlikely
        to exist in tree1, so new hashes are not usually created.
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)    
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite2)
        leaf2 = LeafNode("leaf2", self.tree1, composite2)

        err = self.tree1.add(composite2, composite1)
        assert(not err)

        # check that there are now 8 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 8)

        # check that the original nodes have retained their entries in the
        # registry
        assert(self.tree1.nodes.has_key(composite1.hash))
        assert(self.tree1.nodes.has_key(composite2.hash))
        assert(self.tree1.nodes.has_key(leaf1.hash))
        assert(self.tree1.nodes.has_key(leaf2.hash))
        assert(self.tree1.nodes[composite1.hash] == composite1)
        assert(self.tree1.nodes[composite2.hash] == composite2)
        assert(self.tree1.nodes[leaf1.hash] == leaf1)
        assert(self.tree1.nodes[leaf2.hash] == leaf2)

        # check that the new nodes have entries in the registry
        composite3 = [x for x in composite1.children if x != composite2][0]        
        assert(len(composite3.children) == 2)
        leaf3 = composite3.children[0]
        leaf4 = composite3.children[1]

        assert(self.tree1.nodes.has_key(composite3.hash))
        assert(self.tree1.nodes.has_key(leaf3.hash))
        assert(self.tree1.nodes.has_key(leaf4.hash))
        assert(self.tree1.nodes[composite3.hash] == composite3)
        assert(self.tree1.nodes[leaf3.hash] == leaf3)
        assert(self.tree1.nodes[leaf4.hash] == leaf4)

        # copy a subtree from another tree
        tree2_composite1 = CompositeNode("tree2 composite1", self.tree2, 
            root2)
        tree2_composite2 = CompositeNode("tree2 composite2", self.tree2,
            tree2_composite1)
        tree2_leaf1 = LeafNode("tree2 leaf1", self.tree2, tree2_composite1)
        tree2_leaf2 = LeafNode("tree2 leaf2", self.tree2, tree2_composite2)
        tree2_leaf3 = LeafNode("tree2 leaf3", self.tree2, tree2_composite2)

        # check if tree1 already has the hashes of some of the nodes in tree2
        # if so, new hashes will be created in tree1 upon copying the subtree
        # from tree2, and they should therefore not be checked for
        tree2_composite1_hash_in_tree1 = self.tree1.nodes.has_key(
            tree2_composite1.hash)
        tree2_composite2_hash_in_tree1 = self.tree1.nodes.has_key(
            tree2_composite2.hash)
        tree2_leaf1_hash_in_tree1 = self.tree1.nodes.has_key(
            tree2_leaf1.hash)
        tree2_leaf2_hash_in_tree1 = self.tree1.nodes.has_key(
            tree2_leaf2.hash)
        tree2_leaf3_hash_in_tree1 = self.tree1.nodes.has_key(
            tree2_leaf3.hash) 

        err = self.tree1.add(tree2_composite1, composite1)
        assert(not err)

        # check that there are now 13 nodes in tree1's registry 
        assert(len(self.tree1.nodes.keys()) == 13)
        
        # check that the new nodes have entries in the registry
        tree2_composite1_clone = [x for x in self.tree1.nodes.values() if
                                  x.name == tree2_composite1.name]
        assert(tree2_composite1_clone)
        assert(tree2_composite1_hash_in_tree1 or self.tree1.nodes.has_key(
            tree2_composite1_clone[0].hash))

        tree2_composite2_clone = [x for x in self.tree1.nodes.values() if
                                  x.name == tree2_composite2.name]
        assert(tree2_composite2_clone)
        assert(tree2_composite2_hash_in_tree1 or self.tree1.nodes.has_key(
            tree2_composite2_clone[0].hash))

        tree2_leaf1_clone = [x for x in self.tree1.nodes.values() if
                             x.name == tree2_leaf1.name]
        assert(tree2_leaf1_clone)
        assert(tree2_leaf1_hash_in_tree1 or self.tree1.nodes.has_key(
            tree2_leaf1_clone[0].hash))

        tree2_leaf2_clone = [x for x in self.tree1.nodes.values() if
                             x.name == tree2_leaf2.name]
        assert(tree2_leaf2_clone)
        assert(tree2_leaf2_hash_in_tree1 or self.tree1.nodes.has_key(
            tree2_leaf2_clone[0].hash))

        tree2_leaf3_clone = [x for x in self.tree1.nodes.values() if
                             x.name == tree2_leaf3.name]    
        assert(tree2_leaf3_clone)
        assert(tree2_leaf3_hash_in_tree1 or self.tree1.nodes.has_key(
            tree2_leaf3_clone[0].hash))

    def test_recursive_remove_hash(self):
        """
        Remove a subtree from the root node of a tree. The subtree consists of
        a composite node with a leaf node and a second composite node as its
        children; the second composite node has two leaf nodes as its children.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite2)
        leaf3 = LeafNode("leaf3", self.tree1, composite2)

        # check that there are now 6 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 6)

        err = self.tree1.remove(composite1)
        assert(not err)        

        # check that there is now only 1 node in the registry
        assert(len(self.tree1.nodes.keys()) == 1)

    def test_copy_from_same_tree(self):
        """
        Test the operation of copying a leaf node from one composite node of
        the same tree to another
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leafnode = LeafNode("leaf node", self.tree1, composite1)
        old_hashval = leafnode.hash
        hashes = self.tree1.nodes.keys()

        err = self.tree1.add(leafnode, composite2)
        assert(not err)

        # get the copied leaf node
        new_hashval = [x for x in self.tree1.nodes.keys() if not x in hashes]
        assert(new_hashval) # copied leaf node is in tree1's registry
        new_hashval = new_hashval[0]
        newnode = self.tree1.nodes[new_hashval] 

        # check that there are now five nodes in the tree, including the root
        # node
        assert(len(self.tree1.nodes.keys()) == 5)

        # check that the original leaf node's original parent-child relationship
        # remains intact
        assert(leafnode in composite1.children)
        assert(leafnode.parent == composite1)

        # check that the copied leaf node's new parent-child relationship has
        # been established
        assert(newnode in composite2.children)
        assert(newnode.parent == composite2)

        # check that the original leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(old_hashval == leafnode.hash)
        assert(self.tree1.nodes.has_key(old_hashval))
        assert(self.tree1.nodes[old_hashval] == leafnode)
        
    def test_move_from_same_tree(self):
        """
        Test the operation of moving a leaf node from one composite node
        of the same tree to another
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leafnode = LeafNode("leaf node", self.tree1, composite1)
        hashval = leafnode.hash

        err = self.tree1.add(leafnode, composite2, copying=False)
        assert(not err)

        # check that there are still only four nodes in the tree, 
        # including the root node
        assert(len(self.tree1.nodes.keys()) == 4)

        # check that the leaf node's original parent-child relationship has
        # been terminated
        assert(leafnode not in composite1.children)
        assert(leafnode.parent != composite1)

        # check that the leaf node's new parent-child relationship has been
        # established
        assert(leafnode in composite2.children)
        assert(leafnode.parent == composite2)

        # check that the leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(hashval == leafnode.hash)
        assert(self.tree1.nodes.has_key(hashval))
        assert(self.tree1.nodes[hashval] == leafnode)

    def test_copy_from_other_tree(self):
        """
        Test the operation of copying a leaf node from one tree's root node to
        another tree's root node
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)
        old_hashval = leafnode.hash
        hashes = self.tree2.nodes.keys()

        self.tree2.add(leafnode, root2, source_tree=self.tree1)

        # get the copied leaf node
        new_hashval = [x for x in self.tree2.nodes.keys() if not x in hashes]
        assert(new_hashval) # copied leaf node is in tree2's registry
        new_hashval = new_hashval[0]
        newnode = self.tree2.nodes[new_hashval]

        # check that there are still two nodes in tree1, including the root node
        assert(len(self.tree1.nodes.keys()) == 2)

        # check that there are now two nodes in tree2, including the root node
        assert(len(self.tree2.nodes.keys()) == 2)

        # check that the original leaf node's original parent-child relationship
        # remains intact
        assert(leafnode == root1.children)
        assert(leafnode.parent == root1)

        # check that the copied leaf node's new parent-child relationship has been
        # established
        assert(newnode == root2.children)
        assert(newnode.parent == root2)

        # check that the original leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(old_hashval == leafnode.hash)
        assert(self.tree1.nodes.has_key(old_hashval))
        assert(self.tree1.nodes[old_hashval] == leafnode)

    def test_move_from_other_tree(self):
        """
        Test the operation of moving a leaf node from one tree's root node to
        another tree's root node
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)
        hashval = leafnode.hash

        err = self.tree2.add(leafnode, root2, copying=False, 
            source_tree=self.tree1)
        assert(not err)

        # check that there is now only one node in tree1, i.e. the root node
        assert(len(self.tree1.nodes.keys()) == 1)

        # check that there are now two nodes in tree2, including the root node
        assert(len(self.tree2.nodes.keys()) == 2)

        # check that the original leaf node's original parent-child relationship
        # has been terminated
        assert(leafnode != root1.children)
        assert(leafnode.parent != root1)

        # check that the leaf node's new parent-child relationship has been
        # established
        assert(leafnode == root2.children)
        assert(leafnode.parent == root2)

        # check that the leaf node's hash has been removed from tree1's registry
        assert(not self.tree1.nodes.has_key(hashval))

    def test_add_error_not_node(self):
        """
        Confirm that the attempt to copy or move something that is not a node, or
        to copy or move a node to something that is not a node, returns an error
        message and does not perform any copying or moving operation
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)

        err = self.tree1.add(self.tree1, root2)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.add(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 have 2 and 1 nodes in their registries
        # respectively
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 1)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.nodes.has_key(leafnode.hash))
        assert(self.tree1.nodes[leafnode.hash] == leafnode)

    def test_add_error_root_node(self):
        """
        Confirm that the attempt to copy or move a root node to another root node
        returns an error string and does not copy or move of the root node being
        added
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        err = self.tree1.add(root2, root1, 
            source_tree=self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(root2, root1, copying=False,
            source_tree=self.tree1)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        # check that no root node was created or moved
        assert(len(self.tree1.nodes.keys()) == 1)
        assert(len(self.tree2.nodes.keys()) == 1)
        assert(self.tree1.nodes.has_key(root1.hash))
        assert(self.tree1.nodes[root1.hash] == root1)

    def test_add_error_wrong_tree(self):
        """
        Confirm that the attempt to copy or move a node from tree1 to tree2,
        when source_tree is designated as tree3, will return an error
        and fail to perform the copy or move operation
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)
        
        err = self.tree2.add(leafnode, root2, copying=True,
            source_tree=self.tree3)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree2.add(leafnode, root2, copying=False,
            source_tree=self.tree3)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that no node was created or moved
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 1)
        assert(self.tree1.nodes.has_key(leafnode.hash))
        assert(self.tree1.nodes[leafnode.hash] == leafnode) 

    def test_add_error_leaf_or_non_composite_w_child(self):
        """
        Confirm that the attempt to copy or move a node to a leaf node or
        non-composite node will return an error  string and fail to perform
        the copy or move operation
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite = CompositeNode("composite", self.tree1, root1)
        leaf1 = LeafNode("leaf1", self.tree1, composite) 
        decorator = DecoratorNode("decorator", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, decorator)
        
        err = self.tree1.add(leaf1, leaf2)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, leaf2, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, decorator, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still only 5 nodes in the registry,
        # including the root node
        assert(len(self.tree1.nodes.keys()) == 5)

        # check that leaf1 has not been moved
        assert(leaf1.parent == composite)
        assert(leaf1 in composite.children)

        # check that leaf1 remains in the registry
        assert(self.tree1.nodes.has_key(leaf1.hash))
        assert(self.tree1.nodes[leaf1.hash] == leaf1)

    def test_shift_same_node(self):
        """
        Test the operation of shifting a leaf node to its own position in the
        children list of its parent composite node.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite = CompositeNode("composite", self.tree1, root1) 
        leaf1 = LeafNode("leaf1", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, composite)

        # check that all nodes start out in the right positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)

        err = self.tree1.shift(leaf1, position=0)
        assert(not err)
       
        # check that all nodes are in the same positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)

    def test_shift_siblings(self):
        """
        Test the operation of shifting a leaf node from the second to the fourth
        position of its parent composite node's children list, as well as from
        the first to the last position of that children list.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite = CompositeNode("composite", self.tree1, root1)
        leaf1 = LeafNode("leaf1", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, composite)
        leaf3 = LeafNode("leaf3", self.tree1, composite)
        leaf4 = LeafNode("leaf4", self.tree1, composite)
        leaf5 = LeafNode("leaf5", self.tree1, composite)

        # check that all nodes start out in the right positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)
        assert(composite.children[2] == leaf3)
        assert(composite.children[3] == leaf4)
        assert(composite.children[4] == leaf5)

        err = self.tree1.shift(leaf2, 3)
        assert(not err)        

        # check that leaf2 has been moved to the third position
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf3)
        assert(composite.children[2] == leaf4)
        assert(composite.children[3] == leaf2)
        assert(composite.children[4] == leaf5)

        err = self.tree1.shift(leaf1)
        assert(not err)

        # check that leaf1 has been moved to the final position
        assert(composite.children[0] == leaf3)
        assert(composite.children[1] == leaf4)
        assert(composite.children[2] == leaf2)
        assert(composite.children[3] == leaf5)
        assert(composite.children[4] == leaf1)

    def test_shift_error_not_composite_node(self):
        """
        Confirm that the attempt to shift the child of a non-composite node
        returns an error string 
        """
        root1 = self.tree1.nodes[self.tree1.root]

        decorator = DecoratorNode("decorator", self.tree1, root1)
        leafnode = LeafNode("leaf node", self.tree1, decorator)

        err = self.tree1.shift(leafnode)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.shift(root1)
        assert(isinstance(err, str) or isinstance(err, unicode))

    def test_shift_error_not_node(self):
        """
        Confirm that the attempt to swap something that is not a node, or
        to swap a node with something that is not a node, returns an error
        message
        """
        err = self.tree1.shift(self.tree1)
        assert(isinstance(err, str) or isinstance(err, unicode))

    def test_swap_same_node(self):
        """
        Test the operation of swapping a node with itself, to ensure
        it is valid
        """
        root1 = self.tree1.nodes[self.tree1.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)
        
        self.tree1.swap(leafnode, leafnode)

        # check that there are still only two nodes in the registry,
        # including the root node
        assert(len(self.tree1.nodes.keys()) == 2)

        # check that the leaf node is present in the registry
        assert(self.tree1.nodes.has_key(leafnode.hash))
        assert(self.tree1.nodes[leafnode.hash] == leafnode)

    def test_swap_same_parent(self):
        """
        Test the operation of swapping two leaf nodes that have the same 
        composite node as their parent.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite1)
        leaf3 = LeafNode("leaf3", self.tree1, composite1)

        # check that the children have been placed in the correct order
        assert(composite1.children[0] == leaf1)
        assert(composite1.children[1] == leaf2)
        assert(composite1.children[2] == leaf3)

        err = self.tree1.swap(leaf1, leaf3)
        assert(not err)

        # check that the two swapped nodes have switched places
        assert(composite1.children[0] == leaf3)
        assert(composite1.children[1] == leaf2)
        assert(composite1.children[2] == leaf1)

        # check that the swapped nodes are still in the registry 
        assert(self.tree1.nodes[leaf1.hash] == leaf1)
        assert(self.tree1.nodes[leaf3.hash] == leaf3)

    def test_swap_same_tree(self):
        """
        Test the operation of swapping two leaf nodes whose parents are
        composite nodes parented by the same composite node.

        This tests swapping between two nodes of the same tree and swapping
        between nodes whose parents are composite nodes.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        composite3 = CompositeNode("composite3", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite2)
        leaf2 = LeafNode("leaf2", self.tree1, composite3)

        # check that the parent-child relationships are correct
        assert(composite2.children[0] == leaf1)
        assert(composite3.children[0] == leaf2)
        assert(leaf1.parent == composite2)
        assert(leaf2.parent == composite3)

        err = self.tree1.swap(leaf1, leaf2)
        assert(not err)

        # check that the new parent-child relationships have been established
        assert(composite2.children[0] == leaf2)
        assert(composite3.children[0] == leaf1)
        assert(leaf2.parent == composite2)
        assert(leaf1.parent == composite3)

        # check that the swapped nodes are still in the registry
        assert(self.tree1.nodes[leaf1.hash] == leaf1)
        assert(self.tree1.nodes[leaf2.hash] == leaf2)

    def test_swap_other_tree(self):
        """
        Test the operation of swapping two leaf nodes whose parents are the root
        nodes of two different trees.

        This tests both swapping between two trees and swapping when the parents
        are both non-composite nodes.
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leaf1 = LeafNode("leaf1", self.tree1, root1)
        leaf2 = LeafNode("leaf2", self.tree2, root2)

        assert(root1.children == leaf1)
        assert(root2.children == leaf2)        

        err = self.tree1.swap(leaf2, leaf1, source_tree=self.tree2)
        assert(not err)

        # check that the nodes have been swapped
        assert(root1.children == leaf2)
        assert(root2.children == leaf1)
        assert(leaf2.parent == root1)        
        assert(leaf1.parent == root2)

        # check that each tree's registry has only two nodes, including
        # the root node
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 2)

        # check that the nodes are present in their trees' registries
        assert(self.tree1.nodes.has_key(leaf2.hash))
        assert(self.tree2.nodes.has_key(leaf1.hash))
        assert(self.tree1.nodes[leaf2.hash] == leaf2)
        assert(self.tree2.nodes[leaf1.hash] == leaf1)

        # swap the nodes again
        err = self.tree2.swap(leaf2, leaf1, source_tree=self.tree1)
        
        # check that the nodes have been swapped
        assert(root1.children == leaf1)
        assert(root2.children == leaf2)
        assert(leaf1.parent == root1)
        assert(leaf2.parent == root2)

        # check that the nodes are present in their trees' registries
        assert(self.tree1.nodes.has_key(leaf1.hash))
        assert(self.tree2.nodes.has_key(leaf2.hash))
        assert(self.tree1.nodes[leaf1.hash] == leaf1)
        assert(self.tree2.nodes[leaf2.hash] == leaf2)

    def test_swap_error_not_node(self):
        """
        Confirm that the attempt to swap something that is not a node, or
        to swap a node with something that is not a node, returns an error
        message and does not perform any swapping operation
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)

        err = self.tree1.swap(self.tree1, root2)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.swap(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 have 2 and 1 nodes in their registries
        # respectively
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 1)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.nodes.has_key(leafnode.hash))
        assert(self.tree1.nodes[leafnode.hash] == leafnode)

    def test_swap_error_root_node(self):
        """
        Confirm that the attempt to swap a root node with another node,
        or a node with a root node, returns an error string and does
        not perform the swap
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leaf1 = LeafNode("leaf1", self.tree1, root1)
        leaf2 = LeafNode("leaf2", self.tree2, root2)    

        err = self.tree1.swap(root1, leaf2)
        assert(isinstance(err, str) or isinstance(err, unicode))
        err = self.tree1.swap(leaf1, root2)
        assert(isinstance(err, str) or isinstance(err, unicode))       

        # check that the swap has not been performed
        assert(root1 == root1)
        assert(root2 == root2)

        # check that the leaf nodes have not been moved
        assert(self.tree1.nodes.has_key(leaf1.hash))
        assert(self.tree1.nodes[leaf1.hash] == leaf1)
        assert(self.tree2.nodes.has_key(leaf2.hash))
        assert(self.tree2.nodes[leaf2.hash] == leaf2)

    def test_interpose_same_tree(self):
        """
        Test the operation of copy-interposing and move-interposing a node
        to a different, non-composite node in the same tree.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite = CompositeNode("composite", self.tree1, root1)
        decorator1 = DecoratorNode("decorator1", self.tree1, composite)
        decorator2 = DecoratorNode("decorator2", self.tree1, composite)
        old_hashval = decorator1.hash
        hashes = self.tree1.nodes.keys()

        err = self.tree1.interpose(decorator1, decorator2)
        assert(not err)

        new_hashval = [x for x in self.tree1.nodes.keys() if
                       x not in hashes]
        assert(new_hashval) # copied decorator node is in tree1's registry
        new_hashval = new_hashval[0]
        decorator3 = self.tree1.nodes[new_hashval]

        # check that there are now 5 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 5)

        # check that decorator1 has not been moved
        assert(decorator1 in composite.children)
        assert(decorator1.parent == composite)

        # check that decorator1 is still in the registry
        assert(self.tree1.nodes.has_key(old_hashval))
        assert(self.tree1.nodes[old_hashval] == decorator1)

        # check that the new parent-child relationships for decorator3 have
        # been established
        assert(decorator3 in composite.children)
        assert(decorator3.parent == composite)
        assert(decorator3.children == decorator2)
        assert(decorator2.parent == decorator3)

        err = self.tree1.interpose(decorator1, decorator2, copying=False)
        assert(not err)

        # check that there are still 5 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 5)
        
        # check that the new parent-child relationships for decorator1 have
        # been established
        assert(decorator3.children == decorator1)
        assert(decorator1.parent == decorator3)
        assert(decorator1.children == decorator2)
        assert(decorator2.parent == decorator1)

        # check that the old parent-child relationship for decorator1 has been
        # terminated
        assert(decorator1 not in composite.children)

        # check that decorator1 is still in the registry
        assert(self.tree1.nodes.has_key(old_hashval))
        assert(self.tree1.nodes[old_hashval] == decorator1)

    def test_interpose_composite_node(self):
        """
        Test the operation of copy-interposing and move-interposing a
        composite node onto a target node in the same tree, placing that
        target node in a specific position in the composite node's list of
        children.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        composite1 = CompositeNode("composite1", self.tree1, root1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite1)
        leaf3 = LeafNode("leaf3", self.tree1, composite2)
        leaf4 = LeafNode("leaf4", self.tree1, composite2)
        leaf5 = LeafNode("leaf5", self.tree1, composite2)
        hashes = self.tree1.nodes.keys()

        err = self.tree1.interpose(composite2, leaf1, position=1)
        assert(not err)

        # check that there are now 12 nodes in the tree's registry
        assert(len(self.tree1.nodes.keys()) == 12)

        # get the new composite node
        new_hashval = [x for x in self.tree1.nodes.keys() if
                       self.tree1.nodes[x].name == "composite2" 
                       and x not in hashes]
        assert(new_hashval) # copied composite node is in tree1's registry
        new_hashval = new_hashval[0]
        composite3 = self.tree1.nodes[new_hashval]

        # check that leaf1 is in the appropriate position in composite3's
        # list of children
        assert(composite3.children[1] == leaf1)
        assert(leaf1.parent == composite3)        

        err = self.tree1.interpose(composite2, leaf2, position=None, 
            copying=False)

        # check that there are still 12 nodes in the tree's registry
        assert(len(self.tree1.nodes.keys()) == 12)

        # check that leaf2 is in the appropriate position in composite3's
        # list of children
        assert(composite2.children[3] == leaf2)
        assert(leaf2.parent == composite2)

    def test_interpose_other_tree(self):
        """
        Test the operation of copy-interposing and move-interposing a
        node from one tree to another.
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        decorator1 = DecoratorNode("decorator1", self.tree1, root1)
        decorator2 = DecoratorNode("decorator2", self.tree2, root2)
        old_hashval = decorator1.hash
        hashes = self.tree2.nodes.keys()

        err = self.tree2.interpose(decorator1, decorator2,
            source_tree=self.tree1)
        assert(not err)

        # check that there are now 3 nodes in tree2 and 2 nodes in tree1
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 3)

        # get the new decorator
        new_hashval = [x for x in self.tree2.nodes.keys() if
                       x not in hashes]
        assert(new_hashval)
        new_hashval = new_hashval[0]
        decorator3 = self.tree2.nodes[new_hashval]

        # check that the parent-child relationships of decorator3 have been
        # established
        assert(root2.children == decorator3)
        assert(decorator3.parent == root2)
        assert(decorator3.children == decorator2)
        assert(decorator2.parent == decorator3)

        err = self.tree2.interpose(decorator1, decorator2, copying=False,
            source_tree=self.tree1)
        assert(not err)

        # check that there are now 4 nodes in tree2 and 1 node in tree1
        assert(len(self.tree1.nodes.keys()) == 1)
        assert(len(self.tree2.nodes.keys()) == 4)

        # check that decorator1 has been added to the registry of tree2
        assert(self.tree2.nodes.has_key(decorator1.hash))
        assert(self.tree2.nodes[decorator1.hash] == decorator1)
       
        # check that the parent-child relationships of decorator1 have been
        # established
        assert(decorator3.children == decorator1)
        assert(decorator1.parent == decorator3)
        assert(decorator1.children == decorator2)
        assert(decorator2.parent == decorator1)

    def test_interpose_error_not_node(self):
        """
        Confirm that the attempt to copy-interpose or move-interpose something
        that is not a node, or to copy-interpose or move-interpose a node to
        something that is not a node, returns an error message and does not
        perform any copying or moving operation
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        leafnode = LeafNode("leaf node", self.tree1, root1)
        decorator = DecoratorNode("decorator", self.tree2, root2)

        err = self.tree1.interpose(self.tree1, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.interpose(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 each have 2 nodes in their registries
        assert(len(self.tree1.nodes.keys()) == 2)
        assert(len(self.tree2.nodes.keys()) == 2)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.nodes.has_key(leafnode.hash))
        assert(self.tree1.nodes[leafnode.hash] == leafnode)

    def test_interpose_error_same_node(self):
        """
        Confirm that the attempt to interpose a node onto itself returns
        an error string and does not perform the interposition operation.
        """
        root1 = self.tree1.nodes[self.tree1.root]

        decorator = DecoratorNode("decorator", self.tree1, root1)
        hashval = decorator.hash        

        err = self.tree1.interpose(decorator, decorator, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.interpose(decorator, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still 2 nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 2) 
        
        # check that the decorator node has not been moved
        assert(self.tree1.nodes.has_key(hashval))
        assert(self.tree1.nodes[hashval] == decorator)

    def test_interpose_error_root_node(self):
        """
        Confirm that the attempt to interpose a root node onto another
        node, or a node onto a root node, returns an error string and
        does not perform the interposition.
        """
        root1 = self.tree1.nodes[self.tree1.root]
        root2 = self.tree2.nodes[self.tree2.root]

        decorator = DecoratorNode("decorator1", self.tree1, root1)

        err = self.tree1.interpose(root1, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))
       
        err = self.tree1.interpose(decorator, root2)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still only two nodes in the registry
        assert(len(self.tree1.nodes.keys()) == 2)

        # check that the parent-child relationships of the two nodes in the
        # registry have not changed
        assert(root1.children == decorator)
        assert(root1.parent == None)
        assert(decorator.children == None)
        assert(decorator.parent == root1)


class AdderSuccessLeaf(LeafNode):
    """
    Leaf node that increments a counter and returns Success whenever it ticks
    """
    def update(self, bb):
        bb['nodes'][self.hash]['count'] += 1
        return SUCCESS

    def on_blackboard_setup(self, bb, override=False):
        super(AdderSuccessLeaf, self).on_blackboard_setup(bb, 
            override=override)
        if not bb['nodes'][self.hash].has_key('count') or override:
            bb['nodes'][self.hash]['count'] = 0


class AdderFailureLeaf(LeafNode):
    """
    Leaf node that increments a counter and returns Failure whenever it ticks
    """
    def update(self, bb):
        bb['nodes'][self.hash]['count'] += 1
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        super(AdderFailureLeaf, self).on_blackboard_setup(bb,
            override=override)
        if not bb['nodes'][self.hash].has_key('count') or override:
            bb['nodes'][self.hash]['count'] = 0


class SuccessLeaf(LeafNode):
    """
    Leaf node that always returns Success
    """
    def update(self, bb):
        return SUCCESS


class FailureLeaf(LeafNode):
    """
    Leaf node that always returns Failure
    """
    def update(self, bb):
        return FAILURE


class RunningLeaf(LeafNode):
    """
    Leaf node that always returns Running
    """
    def update(self, bb):
        return RUNNING


class RunToggleLeaf(LeafNode):
    def update(self, bb):
        if bb['nodes'][self.hash]['running']:
            return SUCCESS
        else:
            return RUNNING


class ErrorLeaf(LeafNode):
    """
    Leaf node that always returns Error
    """
    def update(self, bb):
        return ERROR


class ConditionTrue(Condition):
    def condition(self, bb):
        return True


class ConditionFalse(Condition):
    def condition(self, bb):
        return False


class VerifierTrue(Verifier):
    def condition(self, bb):
        return True


class VerifierFalse(Verifier):
    def condition(self, bb):
        return False


class TestFunctionality(TestCase):
    """
    Tests the functionality of behavior trees with various node classes,
    as well as that of their blackboards.
    """
    def setUp(self):
        self.room = create_object(DefaultRoom, key="room", nohome=True)
        self.room.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room.id

        self.tree = create_script(BehaviorTree, key="tree")
        self.target_tree = create_script(BehaviorTree, key="target tree")
        self.agent = create_object(
            AIObject, key="agent", location=self.room, home=self.room)
        self.script = create_script(AIScript, key="script")

    def tearDown(self):
        self.agent.delete()
        self.script.delete()
        self.tree.delete()
        self.target_tree.delete()
        self.room.delete()

    def test_blackboard_setup_spectree(self):
        """
        Test the setup process of the agent and script blackboards when a
        behavior tree is specified as an argument to the setup method
        """
        root = self.tree.nodes[self.tree.root]

        leafnode = LeafNode("leaf", self.tree, root)

        self.agent.ai.setup(tree=self.tree)
        self.script.ai.setup(tree=self.tree)
 
        # check that the agent blackboard's setup was completed successfully
        assert(isinstance(self.agent.ai.agent, AIObject))
        assert(isinstance(self.agent.ai.running_now, _SaverList))
        assert(isinstance(self.agent.ai.running_pre, _SaverList))
        assert(isinstance(self.agent.ai.nodes, _SaverDict))
        assert(isinstance(self.agent.ai.globals, _SaverDict))

        # check that the script blackboard's setup was completed successfully
        assert(isinstance(self.script.ai.agent, AIScript))
        assert(isinstance(self.script.ai.running_now, _SaverList))
        assert(isinstance(self.script.ai.running_pre, _SaverList))
        assert(isinstance(self.script.ai.nodes, _SaverDict))
        assert(isinstance(self.script.ai.globals, _SaverDict))

    def test_blackboard_setup_objtree(self):
        """
        Test the setup process of the agent and script blackboards when a
        behavior tree is specified as an attribute of the object or script
        being assigned a blackboard.
        """
        root = self.tree.nodes[self.tree.root]

        leafnode = LeafNode("leaf", self.tree, root)

        # test setup when a default tree exists
        self.agent.aitree = self.tree
        self.script.aitree = self.tree

        self.agent.ai.setup()
        self.script.ai.setup()
 
        # check that the agent blackboard's setup was completed successfully
        assert(isinstance(self.agent.ai.agent, AIObject))
        assert(isinstance(self.agent.ai.running_now, _SaverList))
        assert(isinstance(self.agent.ai.running_pre, _SaverList))
        assert(isinstance(self.agent.ai.nodes, _SaverDict))
        assert(isinstance(self.agent.ai.globals, _SaverDict))

        # check that the script blackboard's setup was completed successfully
        assert(isinstance(self.script.ai.agent, AIScript))
        assert(isinstance(self.script.ai.running_now, _SaverList))
        assert(isinstance(self.script.ai.running_pre, _SaverList))
        assert(isinstance(self.script.ai.nodes, _SaverDict))
        assert(isinstance(self.script.ai.globals, _SaverDict))

    def test_blackboard_setup_notree(self):
        """
        Test the setup process of the agent and script blackboards when no 
        behavior tree is specified.
        """
        root = self.tree.nodes[self.tree.root]

        leafnode = LeafNode("leaf", self.tree, root)

        self.agent.ai.setup()
        self.script.ai.setup()
 
        # check that the agent blackboard's setup was aborted
        assert(not self.agent.attributes.has("ai"))

        # check that the script blackboard's setup was aborted
        assert(not self.agent.attributes.has("ai"))

    def test_single_leaf(self):
        """
        Test the the ticking of a root-and-leaf tree. 
        """
        root = self.tree.nodes[self.tree.root]

        adder_leaf = AdderSuccessLeaf("adder", self.tree, root)
        self.agent.ai.setup(tree=self.tree)
        self.agent.ai.tick()
        self.agent.ai.tick()
        status = self.agent.ai.tick()
       
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adder_leaf.hash]['count'] == 3)

    def test_aiscript_leaf(self):
        """
        Test the ticking of a root-and-leaf tree associated with an AIScript's
        blackboard.
        """
        root = self.tree.nodes[self.tree.root]

        adder_leaf = AdderSuccessLeaf("adder", self.tree, root)
        self.script.ai.setup(tree=self.tree)
        self.script.ai.tick()
        self.script.ai.tick()
        status = self.script.ai.tick()

        assert(status == SUCCESS)
        assert(self.script.ai.nodes[adder_leaf.hash]['count'] == 3)

    def test_condition_leaf(self):
        """
        Test the ticking of a condition leaf node. 
        """
        root = self.tree.nodes[self.tree.root]

        # check that the node returns Success if the condition is True
        condition = ConditionTrue("condition", self.tree, root)
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the node returns Failure if the condition is False
        self.tree.remove(condition)
        condition = ConditionFalse("condition", self.tree, root)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

    #def test_command_leaf(self):

    def test_transition_leaf(self):
        """
        Test whether a transition leaf successfully transitions to another tree
        """
        root = self.tree.nodes[self.tree.root]
        target_root = self.target_tree.nodes[self.target_tree.root]

        transition = Transition("transition", self.tree, root)
        transition.target_tree = self.target_tree
        adder = AdderSuccessLeaf("adder", self.target_tree, target_root)

        self.agent.ai.setup(tree=self.tree)
        
        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adder.hash]['count'] == 1)

        # check that the target tree can be a string
        transition.target_tree = str(self.target_tree.id)
        self.agent.ai.setup(tree=self.tree, override=True)

        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adder.hash]['count'] == 1)

    def test_echo_leaf(self):
        """
        Test that an echo leaf returns Success when it has a message to send
        and Failure otherwise
        """
        root = self.tree.nodes[self.tree.root]
        echoleaf = EchoLeaf("echoleaf", self.tree, root)
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        echoleaf.msg = "test"
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

    def test_selector(self):
        """
        Test the iteration over a selector with three child nodes, whose first
        node returns Failure, whose third node returns Failure and whose second
        node returns, alternatively, Success, Failure, Running and Error.
        """
        root = self.tree.nodes[self.tree.root]

        selector = Selector("selector", self.tree, root)
        failure1 = FailureLeaf("failure1", self.tree, selector) 
        failurex = FailureLeaf("failurex", self.tree, selector)
        failure3 = FailureLeaf("failure3", self.tree, selector)

        # check that the node returns Failure if all its children return
        # Failure
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == FAILURE)
        
        self.tree.remove(failurex)
        successx = SuccessLeaf("successx", self.tree, selector, position=1)

        # check that the node returns Success if one of its children returns
        # Success
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS) 

        self.tree.remove(successx)
        runningx = RunningLeaf("runningx", self.tree, selector, position=1)

        # check that the node returns Running if one of its children returns
        # Running
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, selector, position=1)

        # check that the node returns Error if one of its children returns
        # Error
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_sequence(self):
        """
        Test the iteration over a sequence with three child nodes, whose first
        node returns Success, whose third node returns Success and whose second
        node returns, alternatively, Success, Failure, Running and Error.
        """
        root = self.tree.nodes[self.tree.root]

        sequence = Sequence("sequence", self.tree, root)
        success1 = SuccessLeaf("success1", self.tree, sequence) 
        successx = SuccessLeaf("successx", self.tree, sequence)
        success3 = SuccessLeaf("success3", self.tree, sequence)

        # check that the node returns Success if all of its children return
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, sequence, position=1)

        # check that the node returns Failure if one of its children returns
        # Failure
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE) 

        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, sequence, position=1)

        # check that the node returns Running if one of its children returns
        # Running
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, sequence, position=1)

        # check that the node returns Error if one of its children returns
        # Error
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_memselector(self):
        """
        Test the iteration over a MemSelector with three child nodes, whose first
        node returns Success, whose third node returns Success and whose second
        node returns, alternatively, Success, Failure, Running and Error.

        Also test that the first child node does not get called again when the
        second node always returns Running and is ticked twice.
        """
        root = self.tree.nodes[self.tree.root]

        memselector = MemSelector("memselector", self.tree, root)
        failure1 = FailureLeaf("failure1", self.tree, memselector)
        failurex = FailureLeaf("failurex", self.tree, memselector)
        failure3 = FailureLeaf("failure3", self.tree, memselector)

        # check that the node returns Failure if all of its children return
        # Failure
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        self.tree.remove(failurex)
        successx = SuccessLeaf("successx", self.tree, memselector, position=1)

        # check that the node returns Success if one of its children returns
        # Success
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        self.tree.remove(successx)
        errorx = ErrorLeaf("errorx", self.tree, memselector, position=1)
        
        # check that the node returns Error if one of its children returns
        # Error
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

        self.tree.remove(errorx)
        runtogglex = RunToggleLeaf("runtogglex", self.tree, memselector, 
            position=1)
        self.tree.remove(failure1)
        adder1 = AdderFailureLeaf("adder1", self.tree, memselector, position=0)

        # check that the node resumes iterating from its running child
        # when ticked again, rather than from the beginning
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adder1.hash]['count'] == 1)

    def test_memsequence(self):
        """
        Test the iteration over a MemSequence with three child nodes, whose first
        node returns Success, whose third node returns Success and whose second
        node returns, alternatively, Success, Failure, Running and Error.

        Also test that the first child node does not get called again when the
        second node always returns Running and is ticked twice.
        """
        root = self.tree.nodes[self.tree.root]

        memsequence = MemSequence("memsequence", self.tree, root)
        success1 = SuccessLeaf("success1", self.tree, memsequence)
        successx = SuccessLeaf("successx", self.tree, memsequence)
        success3 = SuccessLeaf("success3", self.tree, memsequence)

        # check that the node returns Success if all of its children return
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, memsequence, position=1)

        # check that the node returns Failure if one of its children returns
        # Failure
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        self.tree.remove(failurex)
        errorx = ErrorLeaf("errorx", self.tree, memsequence, position=1)
       
        # check that the node returns Error if one of its children returns
        # Error
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

        self.tree.remove(errorx)
        runtogglex = RunToggleLeaf("runtogglex", self.tree, memsequence, 
            position=1)
        self.tree.remove(success1)
        adder1 = AdderSuccessLeaf("adder1", self.tree, memsequence, position=0)
        # check that the node resumes iterating from its running child
        # when ticked again, rather than from the beginning
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adder1.hash]['count'] == 1)

    def test_probselector(self):
        """
        Test that the probability selector always picks a given child when
        all other children have weights of zero

        Also test that the probability selector goes through all children,
        without repeating any of them, when each of them returns Failure. 
        """
        root = self.tree.nodes[self.tree.root]

        probselector = ProbSelector("probselector", self.tree, root)
        adderfailure1 = AdderFailureLeaf("adderfailure1", self.tree, 
            probselector)
        addersuccessx = AdderSuccessLeaf("addersuccessx", self.tree, 
            probselector)
        adderfailure3 = AdderFailureLeaf("adderfailure3", self.tree,
            probselector)

        adderfailure1.weight = 0.0
        addersuccessx.weight = 1.0
        adderfailure3.weight = 0.0

        self.agent.ai.setup(tree=self.tree)
        # check that the weight of nodes corresponds with what was assigned
        near_zero = 0.00001
        assert(abs(self.agent.ai.nodes[adderfailure1.hash]['weight'])
            <= near_zero)
        assert(abs(self.agent.ai.nodes[addersuccessx.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[adderfailure3.hash]['weight']) 
            <= near_zero)

        self.agent.ai.tick()

        # check that only the second node has been ticked
        assert(self.agent.ai.nodes[adderfailure1.hash]['count'] == 0)
        assert(self.agent.ai.nodes[addersuccessx.hash]['count'] == 1)
        assert(self.agent.ai.nodes[adderfailure3.hash]['count'] == 0)

        # check that the node goes through different children each time
        # during a given iteration
        self.tree.remove(addersuccessx)
        adderfailurex = AdderFailureLeaf("adderfailurex", self.tree, 
            probselector, position=1)

        # set all three weights to 1.0 and reset the tree
        adderfailure1.weight = 1.0
        adderfailurex.weight = 1.0
        adderfailure3.weight = 1.0

        self.agent.ai.setup(self.tree, override=True)
        # check that the weight of nodes corresponds with what was assigned
        near_zero = 0.00001
        assert(abs(self.agent.ai.nodes[adderfailure1.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[adderfailurex.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[adderfailure3.hash]['weight'] - 1.0)
            <= near_zero)

        self.agent.ai.tick()
        self.agent.ai.tick()      
        self.agent.ai.tick()

        # check that all the nodes have been ticked once
        assert(self.agent.ai.nodes[adderfailure1.hash]['count'] == 1)
        assert(self.agent.ai.nodes[adderfailurex.hash]['count'] == 1)
        assert(self.agent.ai.nodes[adderfailure3.hash]['count'] == 1)

        # check that a running node will be called repeatedly
        adderfailure1.weight = 0.0
        adderfailure3.weight = 0.0
 
        self.tree.remove(adderfailurex)
        runningx = RunningLeaf("runningx", self.tree, probselector, 
            position=1)
        runningx.weight = 1.0
        self.agent.ai.setup(override=True)

        self.agent.ai.tick()
        self.agent.ai.tick()
        status = self.agent.ai.tick()

        assert(status == RUNNING)
        assert(self.agent.ai.nodes[adderfailure1.hash]['count'] == 0)
        assert(self.agent.ai.nodes[adderfailure3.hash]['count'] == 0)

        # check that ticking an error node returns the correct status
        self.tree.remove(runningx)        
        errorx = ErrorLeaf("errorx", self.tree, probselector, position=1)

        adderfailure1.weight = 0.0
        errorx.weight = 1.0
        adderfailure3.weight = 0.0
        self.agent.ai.setup(override=True)

        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_probsequence(self):
        """
        Test that the probability sequence always picks a given child when
        all other children have weights of zero

        Also test that the probability sequence goes through all children,
        without repeating any of them, when each of them returns Failure. 
        """
        root = self.tree.nodes[self.tree.root]

        probsequence = ProbSequence("probsequence", self.tree, root)
        addersuccess1 = AdderSuccessLeaf("addersuccess1", self.tree, 
            probsequence)
        adderfailurex = AdderFailureLeaf("adderfailurex", self.tree, 
            probsequence)
        addersuccess3 = AdderSuccessLeaf("addersuccess3", self.tree,
            probsequence)

        addersuccess1.weight = 0.0
        adderfailurex.weight = 1.0
        addersuccess3.weight = 0.0

        self.agent.ai.setup(tree=self.tree)
        # check that the weight of nodes corresponds with what was assigned
        near_zero = 0.00001
        assert(abs(self.agent.ai.nodes[addersuccess1.hash]['weight'])
            <= near_zero)
        assert(abs(self.agent.ai.nodes[adderfailurex.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[addersuccess3.hash]['weight']) 
            <= near_zero)

        self.agent.ai.tick()

        # check that only the second node has been ticked
        assert(self.agent.ai.nodes[addersuccess1.hash]['count'] == 0)
        assert(self.agent.ai.nodes[adderfailurex.hash]['count'] == 1)
        assert(self.agent.ai.nodes[addersuccess3.hash]['count'] == 0)

        self.tree.remove(adderfailurex)
        addersuccessx = AdderSuccessLeaf("addersuccessx", self.tree,
            probsequence, position=1)

        # set all three weights to 1.0 and reset the tree
        addersuccess1.weight = 1.0
        addersuccessx.weight = 1.0 # redundancy here
        addersuccess3.weight = 1.0

        self.agent.ai.setup(self.tree, override=True)
        # check that the weight of nodes corresponds with what was assigned
        near_zero = 0.00001
        assert(abs(self.agent.ai.nodes[addersuccess1.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[addersuccessx.hash]['weight'] - 1.0)
            <= near_zero)
        assert(abs(self.agent.ai.nodes[addersuccess3.hash]['weight'] - 1.0)
            <= near_zero)

        self.agent.ai.tick()
        self.agent.ai.tick()      
        self.agent.ai.tick()

        # check that all the nodes have been ticked once
        assert(self.agent.ai.nodes[addersuccess1.hash]['count'] == 1)
        assert(self.agent.ai.nodes[addersuccessx.hash]['count'] == 1)
        assert(self.agent.ai.nodes[addersuccess3.hash]['count'] == 1)

        # check that a running node will be called repeatedly
        addersuccess1.weight = 0.0
        addersuccess3.weight = 0.0
 
        self.tree.remove(addersuccessx)
        runningx = RunningLeaf("runningx", self.tree, probsequence, 
            position=1)
        runningx.weight = 1.0
        self.agent.ai.setup(override=True)

        self.agent.ai.tick()
        self.agent.ai.tick()
        status = self.agent.ai.tick()

        assert(status == RUNNING)
        assert(self.agent.ai.nodes[addersuccess1.hash]['count'] == 0)
        assert(self.agent.ai.nodes[addersuccess3.hash]['count'] == 0)

        # check that ticking an error node returns the correct status
        self.tree.remove(runningx)        
        errorx = ErrorLeaf("errorx", self.tree, probsequence, position=1)

        addersuccess1.weight = 0.0
        errorx.weight = 1.0
        addersuccess3.weight = 0.0
        self.agent.ai.setup(override=True)

        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_parallel(self):
        """
        Test the various possible return policies of a parallel node
        """
        root = self.tree.nodes[self.tree.root]

        parallel = Parallel("parallel", self.tree, root, 
            primary_child=None, req_successes=2, req_failures=2, 
            default_success=True)
        success1 = SuccessLeaf('success1', self.tree, parallel)
        successx = SuccessLeaf('successx', self.tree, parallel)
        failure3 = FailureLeaf('failure3', self.tree, parallel)

        self.agent.ai.setup(tree=self.tree)

        # check that the parallel node returns Success when the requisite
        # number of successes is reached
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the failure of the primary child causes the parallel node
        # to return Failure
        parallel.req_successes = 3
        parallel.primary_child = 2

        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that the parallel node returns Success when the requisite
        # number of successes is reached
        self.tree.remove(successx)
        failurex = FailureLeaf('failurex', self.tree, parallel, position=1)
        parallel.req_successes = 2
        parallel.primary_child = None

        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that the success of the primary child causes the parallel node
        # to return Success
        parallel.primary_child = 0

        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the node returns Success when it completes iterating
        # through its child nodes, default_success is set to True and no other
        # return policies apply
        parallel.primary_child = None
        parallel.req_successes = None
        parallel.req_failures = None
        
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the node returns Failure when it completes iterating
        # through its child nodes, default_success is set to False and no other
        # return policies apply
        parallel.default_success = False
    
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that the node returns Running when one of its children returns
        # Running and none of the other return conditions have been met
        self.tree.remove(failurex)
        runningx = RunningLeaf('runningx', self.tree, parallel, position=1)
        parallel.primary_child = None

        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that the node returns Error when one of its children returns
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf('errorx', self.tree, parallel, position=1)

        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_verifier_true(self):
        """
        Tests the functionality of a verifier node that always returns True
        """
        root = self.tree.nodes[self.tree.root]

        verifier = VerifierTrue("verifier true", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, verifier)

        #print(root.hash, verifier.hash, successx.hash)
        #print(root.children, verifier.children, successx.children)

        # check that this verifier returns Success when its child returns
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that this verifier returns Failure when its child returns
        # Failure
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, verifier)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that this verifier returns Running when its child returns
        # Running
        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, verifier)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that this verifier returns Error when its child returns
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, verifier)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_verifier_false(self):
        """
        Tests the functionality of a verifier node that always returns False
        """
        root = self.tree.nodes[self.tree.root]

        verifier = VerifierFalse("verifier false", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, verifier)

        # check that this verifier returns Failure even when its child returns
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that this verifier coincidentally returns Failure when its child
        # returns Failure
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, verifier) 
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that this verifier returns Failure when its child should return
        # Running
        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, verifier)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that this verifier returns Failure when its child should return
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, verifier)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

    def test_inverter(self):
        """
        Tests the functionality of an inverter node
        """
        root = self.tree.nodes[self.tree.root]

        inverter = Inverter("inverter", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, inverter)

        # check that the inverter returns Failure when its child returns
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        # check that the inverter returns Success when its child returns
        # Failure
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, inverter) 
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the inverter returns Running when its child returns
        # Running
        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, inverter)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that the inverter returns Error when its child returns
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, inverter)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_succeeder(self):
        """
        Tests the functionality of a succeeder node
        """
        root = self.tree.nodes[self.tree.root]

        succeeder = Succeeder("succeeder", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, succeeder)

        # check that the inverter returns Failure when its child returns
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the inverter returns Success even when its child returns
        # Failure
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, succeeder) 
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the inverter returns Running when its child returns
        # Running
        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, succeeder)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that the inverter returns Error when its child returns
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, succeeder)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_failer(self):
        """
        Tests the functionality of a failer node
        """
        root = self.tree.nodes[self.tree.root]

        failer = Failer("failer", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, failer)

        # check that the inverter returns Failure when its child returns
        # Success
        self.agent.ai.setup(tree=self.tree)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the inverter returns Success even when its child returns
        # Failure
        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, failer) 
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        # check that the inverter returns Running when its child returns
        # Running
        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, failer)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that the inverter returns Error when its child returns
        # Error
        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, failer)
        self.agent.ai.setup(override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_repeater(self):
        """
        Test the functionality of a repeater node, checking that it
        runs a given node several times before returning its status.
        """
        root = self.tree.nodes[self.tree.root]

        repeater = Repeater("repeater", self.tree, root)
        adderfailure = AdderFailureLeaf("adderfailure", self.tree, repeater)
        repeater.repeats = 3        

        self.agent.ai.setup(tree=self.tree)
        
        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[adderfailure.hash]['count'] == 3)

    def test_limiter(self):
        """
        Test the functionality of a limiter node, checking that it
        only runs a given node a limited number of times before
        finally returning failure without running it.
        """
        root = self.tree.nodes[self.tree.root]

        limiter = Limiter("limiter", self.tree, root)
        addersuccess = AdderSuccessLeaf("addersuccess", self.tree, limiter)
        limiter.repeats = 2

        self.agent.ai.setup(tree=self.tree)

        status = self.agent.ai.tick()
        assert(status == SUCCESS)
        assert(self.agent.ai.nodes[addersuccess.hash]['count'] == 1)

        self.agent.ai.tick()
        status = self.agent.ai.tick()
        assert(status == FAILURE)
        assert(self.agent.ai.nodes[addersuccess.hash]['count'] == 2)

    def test_allocator(self):
        """
        Test the functionality of the allocator node
        """
        root = self.tree.nodes[self.tree.root]
        allocator = Allocator("allocator", self.tree, root)
        allocator.resources.append("test_resource")
        successx = SuccessLeaf("sucessx", self.tree, allocator)
        self.agent.ai.setup(tree=self.tree)

        # check that the allocator returns its child's status when its
        # resource is taken
        self.agent.ai.globals['resources']['test_resource'] = True
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        # check that the allocator returns its child node's status
        # when the resource is freed
        del self.agent.ai.globals['resources']['test_resource']
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, allocator)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, allocator)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, allocator)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_echo_decorator(self):
        """
        Test that an echo decorator returns the child node's status when there
        is a message to be echoed and returns Failure otherwise.
        """
        root = self.tree.nodes[self.tree.root]
        echodec = EchoDecorator("echodec", self.tree, root)
        successx = SuccessLeaf("successx", self.tree, echodec)
        self.agent.ai.setup(tree=self.tree)

        status = self.agent.ai.tick()
        assert(status == FAILURE)

        echodec.msg = "test"
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == SUCCESS)

        self.tree.remove(successx)
        failurex = FailureLeaf("failurex", self.tree, echodec)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == FAILURE)

        self.tree.remove(failurex)
        runningx = RunningLeaf("runningx", self.tree, echodec)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == RUNNING)

        self.tree.remove(runningx)
        errorx = ErrorLeaf("errorx", self.tree, echodec)
        self.agent.ai.setup(tree=self.tree, override=True)
        status = self.agent.ai.tick()
        assert(status == ERROR)

    def test_tickerhandler(self):
        pass
