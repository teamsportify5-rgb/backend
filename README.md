# Factory Management System - Backend API

FastAPI backend for the Factory Management System.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the backend directory:
```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/factory_management
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

3. Create MySQL database:
```sql
CREATE DATABASE factory_management;
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Orders
- `POST /orders` - Create a new order
- `GET /orders` - Get all orders
- `GET /orders/{id}` - Get order by ID
- `PUT /orders/{id}` - Update order
- `DELETE /orders/{id}` - Delete order

### Attendance
- `POST /attendance/check-in` - Check in
- `POST /attendance/check-out` - Check out
- `GET /attendance/today` - Get today's attendance
- `GET /attendance/employee/{id}` - Get employee attendance

### Payroll
- `POST /payroll/generate/{employee_id}` - Generate payroll
- `GET /payroll/{employee_id}` - Get payroll records
- `GET /payroll/slip/{payroll_id}` - Download payroll slip PDF




