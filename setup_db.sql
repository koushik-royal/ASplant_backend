CREATE DATABASE IF NOT EXISTS plantora;

USE plantora;

-- Clean existing database tables (Commented out to prevent user data loss)
-- DROP TABLE IF EXISTS order_items;
-- DROP TABLE IF EXISTS delivery_tracking;
-- DROP TABLE IF EXISTS delivery_proof;
-- DROP TABLE IF EXISTS payments;
-- DROP TABLE IF EXISTS plant_ratings;
-- DROP TABLE IF EXISTS orders;
-- DROP TABLE IF EXISTS payment_settings;
-- DROP TABLE IF EXISTS qr_payment;
-- DROP TABLE IF EXISTS wishlist;
-- DROP TABLE IF EXISTS cart;
-- DROP TABLE IF EXISTS notifications;
-- DROP TABLE IF EXISTS product_images;
-- DROP TABLE IF EXISTS plants;
-- DROP TABLE IF EXISTS categories;
-- DROP TABLE IF EXISTS otp_verifications;
-- DROP TABLE IF EXISTS customers;
-- DROP TABLE IF EXISTS admins;

-- 1. Customers
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    profile_image VARCHAR(255) DEFAULT '',
    gender VARCHAR(20),
    dob VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    district VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 1.1 OTP Verification
CREATE TABLE IF NOT EXISTS otp_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    otp VARCHAR(6) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL
);

-- 2. Admins
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    profile_image VARCHAR(255) DEFAULT '',
    role VARCHAR(50) DEFAULT 'Admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Categories
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    image_url VARCHAR(255) DEFAULT ''
);

-- 4. Plants
CREATE TABLE IF NOT EXISTS plants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plant_name VARCHAR(100) NOT NULL,
    category_id INT NOT NULL,
    price INT NOT NULL,
    rating DOUBLE DEFAULT 0.0,
    reviews_count INT DEFAULT 0,
    description TEXT,
    benefits VARCHAR(255),
    watering VARCHAR(100),
    sunlight VARCHAR(100),
    pot_size VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active',
    stock INT DEFAULT 25,
    height VARCHAR(50) DEFAULT '30cm',
    weight VARCHAR(50) DEFAULT '1.2kg',
    is_featured BOOLEAN DEFAULT FALSE,
    detailed_description TEXT,
    admin_id INT DEFAULT 1,
    category VARCHAR(100) DEFAULT 'Indoor',
    image_url VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);

-- 5. Product Images
CREATE TABLE IF NOT EXISTS product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    display_order INT DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES plants (id) ON DELETE CASCADE
);

-- 6. Wishlist
CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    plant_id INT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product_wishlist (customer_id, plant_id)
);

-- 7. Cart
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    plant_id INT NOT NULL,
    quantity INT DEFAULT 1,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product_cart (customer_id, plant_id)
);

-- 8. Orders
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    date VARCHAR(100) NOT NULL,
    order_status VARCHAR(50) DEFAULT 'Pending',
    subtotal INT NOT NULL,
    delivery_charge INT NOT NULL,
    total_amount INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    address_line VARCHAR(255) NOT NULL,
    landmark VARCHAR(100) DEFAULT '',
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    country VARCHAR(100),
    address_type VARCHAR(20) DEFAULT 'HOME',
    delivery_type VARCHAR(50) DEFAULT 'Standard Delivery',
    payment_method VARCHAR(50) NOT NULL,
    delivery_proof_path VARCHAR(255) DEFAULT '',
    customer_signature_path VARCHAR(255) DEFAULT '',
    payment_status VARCHAR(50) DEFAULT 'UNPAID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

-- 9. Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    plant_id INT NOT NULL,
    quantity INT NOT NULL,
    price INT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (order_number) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE
);

-- 10. Delivery Tracking
CREATE TABLE IF NOT EXISTS delivery_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255) DEFAULT '',
    FOREIGN KEY (order_id) REFERENCES orders (order_number) ON DELETE CASCADE
);

-- 11. Delivery Proof
CREATE TABLE IF NOT EXISTS delivery_proof (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    signature_path VARCHAR(255) NOT NULL,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (order_number) ON DELETE CASCADE
);

-- 12. Payments
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    customer_id INT NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    amount INT NOT NULL,
    transaction_id VARCHAR(100) DEFAULT '',
    status VARCHAR(50) DEFAULT 'UNPAID',
    screenshot_path VARCHAR(255) DEFAULT '',
    verified_at TIMESTAMP NULL DEFAULT NULL,
    verified_by INT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (order_number) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
);

-- 13. Payment Settings
CREATE TABLE IF NOT EXISTS payment_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cod_enabled BOOLEAN DEFAULT TRUE,
    bank_name VARCHAR(100) DEFAULT 'State Bank of India',
    account_number VARCHAR(50) DEFAULT '123456789012',
    ifsc_code VARCHAR(20) DEFAULT 'SBIN0001234',
    account_holder VARCHAR(100) DEFAULT 'AS Plants Admin',
    express_delivery_charge INT DEFAULT 79
);

-- 14. QR Payments
CREATE TABLE IF NOT EXISTS qr_payment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    upi_id VARCHAR(100) NOT NULL,
    qr_image VARCHAR(255) DEFAULT '',
    active BOOLEAN DEFAULT TRUE,
    updated_by_admin INT DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 15. Plant Ratings
CREATE TABLE IF NOT EXISTS plant_ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plant_id INT NOT NULL,
    customer_id INT NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    rating DOUBLE NOT NULL,
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders (order_number) ON DELETE CASCADE
);

-- 16. Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES customers (id) ON DELETE CASCADE
);

-- ==========================================
-- SEED DATA
-- ==========================================

-- Seed Categories
INSERT IGNORE INTO
    categories (id, name, image_url)
VALUES (1, 'Succulents', ''),
    (2, 'Indoor', ''),
    (3, 'Bonsai', ''),
    (4, 'Outdoor', ''),
    (5, 'Flowering', ''),
    (6, 'Free', '');
-- Seed Products (Removed all default hardcoded plants)

-- Seed Default Admin & Customer
-- Default Admin: admin@plantora.com / password: adminpassword (hashed)
INSERT IGNORE INTO
    admins (
        email,
        password_hash,
        name,
        phone,
        role
    )
VALUES (
        'admin@plantora.com',
        '$pbkdf2-sha256$29000$DAHg/B.jlFIq5ZxzTmktRQ$ccAsz2h7p/Qz3OfBBHRvRBizZvJOFM1GzpH9lNe0IsA',
        'Super Admin',
        '+91 98765 43210',
        'Super Admin'
    );

-- Default Customer: alex.mercer@plantora.com / password: customerpassword (hashed)
INSERT IGNORE INTO
    customers (
        email,
        password_hash,
        name,
        phone,
        gender,
        dob,
        address,
        city,
        state,
        pincode
    )
VALUES (
        'alex.mercer@plantora.com',
        '$pbkdf2-sha256$29000$Z.x9L6V0DgHAWIvxfi/FmA$URrEhfBej6sSmx.E2aJ9.TOJRT.vK/T74mhRFKHDNX8',
        'Alex Mercer',
        '+91 98765 43210',
        'Male',
        '12 Aug 1995',
        '123, Green Park Layout, Near Central Mall',
        'Bangalore',
        'Karnataka',
        '560001'
    );

-- Seed Default Settings
INSERT IGNORE INTO
    payment_settings (
        id,
        cod_enabled,
        bank_name,
        account_number,
        ifsc_code,
        account_holder,
        express_delivery_charge
    )
VALUES (
        1,
        TRUE,
        'State Bank of India',
        '123456789012',
        'SBIN0001234',
        'AS Plants Admin',
        79
    );

-- Seed Default QR codes (specifying explicit IDs and using INSERT IGNORE)
INSERT IGNORE INTO
    qr_payment (
        id,
        account_name,
        upi_id,
        qr_image,
        active
    )
VALUES (
        1,
        'Google Pay',
        'admin@okaxis',
        'http://10.0.2.2:8000/static/qr_mock.png',
        TRUE
    ),
    (
        2,
        'PhonePe',
        'admin@ybl',
        'http://10.0.2.2:8000/static/qr_mock.png',
        TRUE
    ),
    (
        3,
        'Paytm',
        'admin@paytm',
        'http://10.0.2.2:8000/static/qr_mock.png',
        TRUE
    );

-- Seed Default Notifications (specifying explicit ID and using INSERT IGNORE)
INSERT IGNORE INTO
    notifications (
        id,
        user_id,
        title,
        message,
        type,
        is_read
    )
VALUES (
        1,
        1,
        'Welcome to AS Plants!',
        'Start exploring our premium plants catalog.',
        'system',
        FALSE
    );