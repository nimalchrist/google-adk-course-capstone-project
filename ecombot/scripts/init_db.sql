-- init_db.sql — eComBot seed schema
-- Runs once on first Postgres container start.
-- Idempotent: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.

-- ── Orders ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR(20)  PRIMARY KEY,
    customer_name   VARCHAR(100) NOT NULL,
    customer_email  VARCHAR(100),
    product_name    VARCHAR(100) NOT NULL,
    quantity        INTEGER      NOT NULL DEFAULT 1,
    status          VARCHAR(20)  NOT NULL DEFAULT 'Processing',
    eta             VARCHAR(50),
    carrier         VARCHAR(50),
    total_amount    NUMERIC(10,2),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ── Products ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(20)  PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    price           NUMERIC(10,2) NOT NULL,
    stock           INTEGER      NOT NULL DEFAULT 0,
    description     TEXT,
    specs           JSONB,
    status          VARCHAR(20)  NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ── Durable conversation history ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS session_history (
    id          BIGSERIAL    PRIMARY KEY,
    session_id  VARCHAR(100) NOT NULL,
    user_id     VARCHAR(100) NOT NULL,
    role        VARCHAR(20)  NOT NULL,
    content     TEXT         NOT NULL,
    tool_calls  JSONB,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sh_session ON session_history (session_id, created_at);

-- ── Order seed data ───────────────────────────────────────────────────────
INSERT INTO orders (order_id, customer_name, customer_email, product_name, quantity, status, eta, carrier, total_amount)
VALUES
    ('ORD-001', 'Priya Sharma',  'priya@example.com',  'iPhone 15 Pro',        1, 'Shipped',     '15 Jun 2026', 'BlueDart',  134900.00),
    ('ORD-002', 'Ravi Kumar',    'ravi@example.com',   'Samsung Galaxy S24',    1, 'Processing',  '18 Jun 2026', 'DTDC',       79999.00),
    ('ORD-003', 'Meera Nair',    'meera@example.com',  'Sony WH-1000XM5',      1, 'Delivered',   'Already delivered', 'FedEx', 29990.00),
    ('ORD-004', 'John Mathews',  'john@example.com',   'MacBook Air M3',        1, 'Shipped',     '16 Jun 2026', 'Delhivery', 114900.00),
    ('ORD-005', 'Aisha Mehta',   'aisha@example.com',  'iPad Air',              1, 'Cancelled',   NULL,            NULL,         59900.00),
    ('ORD-006', 'Kenji Tanaka',  'kenji@example.com',  'Pixel 9 Pro',          1, 'Processing',  '20 Jun 2026', 'BlueDart',   109999.00),
    ('ORD-007', 'Fatima Al-Ali', 'fatima@example.com', 'AirPods Pro 2',        2, 'Shipped',     '14 Jun 2026', 'FedEx',      49980.00)
ON CONFLICT (order_id) DO NOTHING;

-- ── Product seed data ─────────────────────────────────────────────────────
INSERT INTO products (product_id, name, category, price, stock, description, specs, status)
VALUES
    ('PRD-101', 'iPhone 15 Pro',       'Smartphones',   134900.00, 25,
     'Apple iPhone 15 Pro with A17 Pro chip, titanium design, and 48MP camera system.',
     '{"display": "6.1 inch Super Retina XDR", "chip": "A17 Pro", "storage": "256GB", "camera": "48MP triple", "battery": "3274mAh"}',
     'active'),
    ('PRD-102', 'Samsung Galaxy S24',  'Smartphones',    79999.00, 40,
     'Samsung Galaxy S24 with Galaxy AI, Dynamic AMOLED 2X display, and 50MP camera.',
     '{"display": "6.2 inch Dynamic AMOLED 2X", "chip": "Exynos 2400", "storage": "128GB", "camera": "50MP triple", "battery": "4000mAh"}',
     'active'),
    ('PRD-103', 'Sony WH-1000XM5',    'Audio',          29990.00, 60,
     'Industry-leading noise canceling headphones with Auto NC Optimizer and 30-hour battery.',
     '{"type": "Over-ear", "driver": "30mm", "anc": "Yes", "battery_hours": 30, "weight_g": 250}',
     'active'),
    ('PRD-104', 'MacBook Air M3',      'Laptops',       114900.00, 15,
     'Apple MacBook Air with M3 chip, 15.3-inch Liquid Retina display, and 18-hour battery.',
     '{"display": "15.3 inch Liquid Retina", "chip": "M3", "ram": "8GB", "storage": "256GB SSD", "battery_hours": 18}',
     'active'),
    ('PRD-105', 'iPad Air',            'Tablets',        59900.00,  0,
     'Apple iPad Air with M1 chip and 10.9-inch Liquid Retina display.',
     '{"display": "10.9 inch Liquid Retina", "chip": "M1", "storage": "64GB", "camera": "12MP"}',
     'out_of_stock'),
    ('PRD-106', 'Pixel 9 Pro',         'Smartphones',   109999.00, 30,
     'Google Pixel 9 Pro with Tensor G4 chip, AI features, and 50MP triple camera.',
     '{"display": "6.3 inch Super Actua", "chip": "Tensor G4", "storage": "128GB", "camera": "50MP triple", "battery": "4700mAh"}',
     'active'),
    ('PRD-107', 'AirPods Pro 2',       'Audio',          24990.00, 100,
     'Apple AirPods Pro 2nd gen with H2 chip, Adaptive Transparency, and USB-C.',
     '{"type": "In-ear TWS", "chip": "H2", "anc": "Yes", "battery_hours": 6, "case_battery_hours": 30}',
     'active'),
    ('PRD-108', 'Nothing Phone 2a',    'Smartphones',    23999.00,  0,
     'Nothing Phone (2a) with unique Glyph interface and Dimensity 7200 Pro.',
     '{"display": "6.7 inch AMOLED", "chip": "Dimensity 7200 Pro", "storage": "128GB", "camera": "50MP dual"}',
     'inactive')
ON CONFLICT (product_id) DO NOTHING;
