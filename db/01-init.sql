CREATE TABLE books (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  isbn TEXT UNIQUE,
  quantity INT NOT NULL DEFAULT 1 CHECK (quantity >= 0)
);
CREATE TABLE members (
  id SERIAL PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT UNIQUE,
  phone TEXT,
  created_at TIMESTAMP DEFAULT now()
);
CREATE TABLE loans (
  id SERIAL PRIMARY KEY,
  book_id INT NOT NULL REFERENCES books(id),
  member_id INT NOT NULL REFERENCES members(id),
  borrowed_at DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE NOT NULL,
  returned_at DATE
);
INSERT INTO books (title, author, isbn, quantity) VALUES
 ('Lập trình Python cơ bản', 'Nguyễn Văn An', '978-604-0001', 5),
 ('Cơ sở dữ liệu', 'Trần Thị Bình', '978-604-0002', 3),
 ('Mạng máy tính', 'Lê Minh Châu', '978-604-0003', 4),
 ('Clean Code', 'Robert C. Martin', '978-013-2350', 2),
 ('Docker in Practice', 'Ian Miell', '978-161-7292', 2);
INSERT INTO members (full_name, email, phone) VALUES
 ('Phạm Hoàng Nam', 'nam@example.com', '0901000001'),
 ('Đỗ Thu Hà', 'ha@example.com', '0901000002'),
 ('Vũ Quang Huy', 'huy@example.com', '0901000003');
