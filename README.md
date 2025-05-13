# SmartUrl

> A modern URL shortening and QR code generation service built with FastAPI and PostgreSQL.

SmartUrl provides a robust API for creating short URLs, QR codes, and barcodes with built-in analytics. The service is designed for scalability, using AWS S3 for image storage and AWS RDS for database management.

## 🚀 Features

- **URL Shortening** - Convert long URLs to compact, shareable links
- **QR Code Generation** - Create scannable QR codes for any URL
- **Barcode Creation** - Generate barcodes linked to destinations
- **User Management** - Register, login, and track your resources
- **History Tracking** - View your created links, QR codes, and barcodes
- **Title Extraction** - Automatically extract webpage titles
- **Analytics** - Track clicks, scans, and engagement metrics
- **AWS Integration** - S3 for image storage, RDS for database
- **Performance Optimized** - Redis caching and counter batching
- **Rate Limiting** - Tiered protection against API abuse

## 📋 Prerequisites

- Python 3.8+
- Docker and Docker Compose
- AWS Account (for S3 and RDS)
- PostgreSQL client (for development)

## 🔧 Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/smarturl.git
cd smarturl
```

2. **Create and activate virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file in the project root:

```
# Database configuration
DB_HOST=your-instance.xxxxx.region.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=smarturl

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TTL=3600

# AWS configuration
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=your_region
S3_BUCKET_NAME=your-bucket-name

# JWT Authentication
JWT_SECRET=your-secret-key-for-jwt
JWT_ACCESS_EXPIRE=3600
JWT_REFRESH_EXPIRE=604800
```

4. **Start Redis via Docker**

```bash
docker-compose up -d
```

5. **Run the application**

```bash
python main.py
```

## Authentication Configuration Explained

The JWT authentication system requires three environment variables:

- **JWT_SECRET**: This is the secret key used to sign and verify JWT tokens. You should generate a secure random string for this. For example:
  ```bash
  # Generate a random secret key using Python
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- **JWT_ACCESS_EXPIRE**: The lifespan of access tokens in seconds. The default is 3600 (1 hour). 
  - Short-lived access tokens improve security
  - Adjust based on your security requirements

- **JWT_REFRESH_EXPIRE**: The lifespan of refresh tokens in seconds. The default is 604800 (7 days).
  - Longer-lived refresh tokens reduce the need for users to log in frequently
  - Users can get new access tokens without re-authenticating until this expires

## 📝 Configuration

### AWS Setup

#### RDS PostgreSQL Configuration

1. Create an RDS PostgreSQL instance in the AWS Console
2. Configure a security group to allow traffic from your application
3. Set the master username, password, and database name
4. Update your `.env` file with the connection details

#### S3 Bucket Configuration

1. Create an S3 bucket for storing QR codes and barcodes
2. Configure the bucket for public read access
3. Set up appropriate CORS configuration
4. Update your `.env` file with bucket details

## 📊 Development

### Code Quality

The codebase follows several best practices to maintain quality and improve maintainability:

- **Standardized Documentation**: Google-style docstrings are used throughout the codebase to provide consistent documentation
- **Design Patterns**: Base classes like `BaseCodeService` reduce code duplication for similar services
- **Caching Strategy**: Redis is used for caching with appropriate TTLs and fallback mechanisms
- **Error Handling**: Consistent error handling patterns with proper logging
- **Modular Architecture**: Clear separation of concerns between API routes, services, and data access layers

### Project Structure

```
smarturl/
├── app/
│   ├── api/
│   │   ├── auth_routes.py     # User authentication routes
│   │   ├── history_routes.py  # History tracking routes
│   │   └── url_routes.py      # URL, QR code, and barcode routes
│   ├── models/
│   │   ├── history_schema.py  # History-related schemas
│   │   ├── url_schemas.py     # URL-related schemas
│   │   └── user_schema.py     # User-related schemas
│   ├── services/
│   │   ├── url_service.py      # URL shortening service
│   │   ├── qr_service.py       # QR code generation service
│   │   ├── barcode_service.py  # Barcode generation service
│   │   ├── base_code_service.py # Shared base for codes
│   │   └── s3_service.py       # AWS S3 integration service
│   ├── database/
│   │   ├── history_db.py      # History retrieval functions
│   │   ├── url_db.py          # URL-related database operations
│   │   └── user_db.py         # User-related database operations
│   └── cache/
│       ├── redis_client.py    # Redis caching functionality
│       └── cache_manager.py   # Cache management utilities
├── main.py                    # Application entry point
├── requirements.txt           # Project dependencies
├── .env                       # Environment variables
└── docker-compose.yml         # Docker services configuration
```

### Local Development with Docker

For local development with a PostgreSQL container instead of RDS:

```bash
# Use the local development docker-compose file
docker-compose -f docker-compose.dev.yml up -d
```

### Connection Verification

During setup, you can verify that your connections to required services are working correctly through the application's startup sequence. The application checks connections to:

- PostgreSQL database
- Redis cache
- S3 storage

If any connection issues occur, they will be logged at startup.

### Connecting to AWS Services

For development purposes, you can connect to AWS services through an EC2 jump host using an SSH tunnel:

1. The repository includes `SmartUrl-KeyPair.pem` for connecting to the EC2 jump host. Make sure it has the proper permissions:
   ```bash
   chmod 600 SmartUrl-KeyPair.pem
   ```

2. Use the `tunnel.sh` script to create SSH tunnels to AWS services:
   ```bash
   ./tunnel.sh
   ```

   This sets up local port forwarding:
   - PostgreSQL: localhost:5432 → RDS instance
   - Redis: localhost:6379 → ElastiCache instance

3. Test the connectivity to ensure all services are accessible:
   ```bash
   python test_aws_connections.py
   ```

   This will verify your connections to PostgreSQL, Redis, and S3.

4. To close the tunnel when you're done:
   ```bash
   pkill -f 'ssh -i.*smarturl'
   ```

**Note:** In a production environment, the private key would typically not be included in the repository. We've included it here for development simplicity.

## Using the API

### Authentication

**Register a new user**:
```
POST /auth/register
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Login**:
```
POST /auth/login
{
  "username": "johndoe",
  "password": "securepassword"
}
```

**Access protected endpoints**:
Include the JWT token in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Creating Resources

**Create short URL**:
```
POST /shorten/
{
  "target_url": "https://example.com/your/long/url"
}
```

**Create QR code**:
```
POST /qrcode/
{
  "target_url": "https://example.com/your/long/url"
}
```

**Create barcode**:
```
POST /barcode/
{
  "target_url": "https://example.com/your/long/url"
}
```

### Viewing History

**Get URL history**:
```
GET /urls/history?page=1&limit=20&sort_field=created_at&sort_order=desc
```

**Get QR code history**:
```
GET /qrcodes/history?page=1&limit=20&sort_field=created_at&sort_order=desc
```

**Get barcode history**:
```
GET /barcodes/history?page=1&limit=20&sort_field=created_at&sort_order=desc
```

All history endpoints support the following parameters:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `sort_field`: Field to sort by (`created_at` or `clicks`/`scans`)
- `sort_order`: Sort direction (`asc` or `desc`)

## 🚢 Deployment

### Administrative Endpoints

The application provides several admin endpoints for maintenance:

**Sync click counts**:
```
GET /admin/sync-clicks
```

**Cache management**:
```
GET /auth/admin/cache/stats
POST /auth/admin/cache/clear/{entity_type}
GET /auth/admin/redis/info
```

### Production Considerations

- Set up proper monitoring and logging
- Configure HTTPS with a valid SSL certificate
- Implement authentication for administrative endpoints
- Use managed services (AWS ECS/EKS) for container orchestration
- Set up CloudFront for content delivery
- Configure scheduled tasks for cache synchronization
- Implement proper database backup strategies

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)
- [AWS](https://aws.amazon.com/)
- [QR Code](https://pypi.org/project/qrcode/)
- [python-barcode](https://pypi.org/project/python-barcode/)

## 🧩 Code Structure Highlights

The architecture follows a modular design with several noteworthy patterns:

1. **Service Layer Pattern**: Business logic is encapsulated in service modules
2. **Repository Pattern**: Database access is isolated in database modules
3. **Dependency Injection**: FastAPI's dependency system for clean API routes
4. **Caching Layer**: Redis caching with proper invalidation strategies
5. **Base Service Inheritance**: Common code isolated in base service classes
6. **Consistent Error Handling**: Standardized approach to error handling and logging