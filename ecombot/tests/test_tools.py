"""
test_tools.py — Quick integration test for eComBot tools (mock data only)
"""
import sys
sys.path.insert(0, '.')

from src.tools.order_tools import get_order_status, cancel_order, save_customer_name, get_session_summary
from src.tools.product_tools import lookup_product, check_stock


class MockToolContext:
    def __init__(self):
        self.state = {}


def test_all():
    # Test 1: Valid order
    ctx = MockToolContext()
    result = get_order_status('ORD-001', ctx)
    assert result['found'] == True
    assert result['status'] == 'Shipped'
    assert ctx.state['current_order_id'] == 'ORD-001'
    print('✓ Test 1: get_order_status(ORD-001) — Shipped')

    # Test 2: Invalid format
    ctx = MockToolContext()
    result = get_order_status('XYZ-123', ctx)
    assert result['found'] == False
    assert 'Invalid order ID format' in result['error']
    print('✓ Test 2: get_order_status(XYZ-123) — invalid format error')

    # Test 3: Not found
    ctx = MockToolContext()
    result = get_order_status('ORD-999', ctx)
    assert result['found'] == False
    assert 'not found' in result['error']
    print('✓ Test 3: get_order_status(ORD-999) — not found')

    # Test 4: Cancel order
    ctx = MockToolContext()
    result = cancel_order('ORD-002', ctx)
    assert result['cancelled'] == True
    print('✓ Test 4: cancel_order(ORD-002) — cancelled OK')

    # Test 5: Cancel already cancelled
    ctx = MockToolContext()
    result = cancel_order('ORD-005', ctx)
    assert result['cancelled'] == False
    assert 'already cancelled' in result['error']
    print('✓ Test 5: cancel_order(ORD-005) — already cancelled')

    # Test 6: Save customer name
    ctx = MockToolContext()
    result = save_customer_name('Priya', ctx)
    assert result['saved'] == True
    assert ctx.state['customer_name'] == 'Priya'
    print('✓ Test 6: save_customer_name(Priya) — saved OK')

    # Test 7: Product lookup
    ctx = MockToolContext()
    result = lookup_product('iPhone', ctx)
    assert result['found'] == True
    assert len(result['results']) > 0
    print(f"✓ Test 7: lookup_product(iPhone) — found {len(result['results'])} products")

    # Test 8: Stock check - out of stock
    ctx = MockToolContext()
    result = check_stock('PRD-105', ctx)
    assert result['available'] == False
    print('✓ Test 8: check_stock(PRD-105/iPad Air) — out of stock')

    # Test 9: Stock available
    ctx = MockToolContext()
    result = check_stock('PRD-101', ctx)
    assert result['available'] == True
    print(f"✓ Test 9: check_stock(PRD-101) — in stock ({result['stock_count']} units)")

    # Test 10: Session summary
    ctx = MockToolContext()
    ctx.state['customer_name'] = 'Priya'
    ctx.state['current_order_id'] = 'ORD-001'
    result = get_session_summary(ctx)
    assert result['customer_name'] == 'Priya'
    print('✓ Test 10: get_session_summary — correct state')

    print()
    print('=' * 50)
    print('  ALL 10 TOOL TESTS PASSED')
    print('=' * 50)


if __name__ == '__main__':
    test_all()
