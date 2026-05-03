CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE ingredients (
    ingredient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    density DECIMAL(10,4),
    thermal_property VARCHAR(50),
    element VARCHAR(50)
);

CREATE TABLE inventory (
    ingredient_id UUID REFERENCES ingredients(ingredient_id),
    qty DECIMAL(10,3),
    unit VARCHAR(20),
    expiry_date DATE,
    PRIMARY KEY (ingredient_id)
);

CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor VARCHAR(255),
    date DATE
);

CREATE TABLE receipt_line (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_id UUID REFERENCES receipts(id),
    ingredient_id UUID REFERENCES ingredients(ingredient_id),
    qty DECIMAL(10,3),
    unit VARCHAR(20),
    price DECIMAL(10,2)
);
