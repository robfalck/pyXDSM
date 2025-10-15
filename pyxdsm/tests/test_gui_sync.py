#!/usr/bin/env python3
"""Test that GUI synchronization with XDSM works correctly."""

import pyxdsm.draganddrop as dnd
from pyxdsm.XDSM import XDSM
from pyxdsm.gui import XDSMGUI, build_disciplines_from_xdsm


def test_reorder_systems():
    """Test that reordering systems in the GUI updates the XDSM."""
    # Create a sample XDSM with 4 systems
    xdsm = XDSM()
    xdsm.add_system('opt', 'Optimization', 'Optimization')
    xdsm.add_system('d1', 'Function', 'Analysis 1')
    xdsm.add_system('d2', 'Function', 'Analysis 2')
    xdsm.add_system('d3', 'Function', 'Analysis 3')

    # Create GUI instance
    gui = XDSMGUI(xdsm=xdsm)

    # Build disciplines from XDSM
    disciplines = build_disciplines_from_xdsm(gui.xdsm)

    # Verify initial order
    initial_order = [sys.node_name for sys in gui.xdsm.systems]
    print(f"Initial order: {initial_order}")
    assert initial_order == ['opt', 'd1', 'd2', 'd3']

    # Simulate a drag-and-drop: move 'opt' (index 0) to position 2
    # This simulates dragging the first element to the third position
    reordered_disciplines = [disciplines[1], disciplines[2], disciplines[0], disciplines[3]]

    # Call sync_from_disciplines (this is what on_reorder does)
    gui.sync_from_disciplines(reordered_disciplines)

    # Verify new order
    new_order = [sys.node_name for sys in gui.xdsm.systems]
    print(f"After reorder: {new_order}")
    assert new_order == ['d1', 'd2', 'opt', 'd3']

    print("✓ Test passed: Systems reordered correctly in XDSM")


def test_reorder_with_matching():
    """Test that sync_from_disciplines correctly matches titles to systems."""
    # Create XDSM
    xdsm = XDSM()
    xdsm.add_system('opt', 'Optimization', 'My Optimizer')
    xdsm.add_system('analysis', 'Function', 'My Analysis')
    xdsm.add_system('solver', 'MDA', 'My Solver')

    gui = XDSMGUI(xdsm=xdsm)

    # Build disciplines
    disciplines = build_disciplines_from_xdsm(gui.xdsm)

    # Verify titles match
    assert disciplines[0].title == 'My Optimizer'
    assert disciplines[1].title == 'My Analysis'
    assert disciplines[2].title == 'My Solver'

    # Reverse the order
    reordered = [disciplines[2], disciplines[1], disciplines[0]]
    gui.sync_from_disciplines(reordered)

    # Verify XDSM was updated
    new_order = [sys.node_name for sys in gui.xdsm.systems]
    print(f"Reversed order: {new_order}")
    assert new_order == ['solver', 'analysis', 'opt']

    print("✓ Test passed: Title matching works correctly")


if __name__ == '__main__':
    test_reorder_systems()
    test_reorder_with_matching()
    print("\n✓ All tests passed!")
