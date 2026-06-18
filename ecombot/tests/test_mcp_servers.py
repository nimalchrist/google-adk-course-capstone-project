import subprocess
import sys
import os
import time
import socket
import json

MCP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_servers')
PYTHON = sys.executable


def test_orders_server():
    server_path = os.path.join(MCP_DIR, 'orders_server.py')
    host, port = '127.0.0.1', 18766  # Use non-default port for testing

    proc = subprocess.Popen(
        [PYTHON, server_path],
        env={**os.environ, 'ORDERS_SERVER_HOST': host, 'ORDERS_SERVER_PORT': str(port)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        deadline = time.monotonic() + 5
        started = False
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    started = True
                    break
            except OSError:
                time.sleep(0.1)

        if started:
            print(f'✓ Orders MCP server started on {host}:{port}')
        else:
            print(f'✗ Orders MCP server failed to start')
            return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        print('  Server stopped.')

    return True


def test_inventory_server_import():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'inventory_server',
        os.path.join(MCP_DIR, 'inventory_server.py'),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, 'check_stock')
    assert hasattr(mod, 'list_variants')
    print('✓ Inventory server module imports OK')
    print('  Tools: check_stock, list_variants')
    return True


if __name__ == '__main__':
    results = []
    results.append(test_orders_server())
    results.append(test_inventory_server_import())

    print()
    if all(results):
        print('=' * 50)
        print('  ALL MCP SERVER TESTS PASSED')
        print('=' * 50)
    else:
        print('SOME TESTS FAILED')
        sys.exit(1)
