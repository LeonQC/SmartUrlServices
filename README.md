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
- AWS Account (for S3, RDS, and ElastiCache)
- SSH client (for connecting to EC2 jump host)
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
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=smarturl

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TTL=3600
REDIS_SSL=false

# AWS configuration
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=eu-west-2
S3_BUCKET_NAME=your-bucket-name

# JWT Authentication
JWT_SECRET=your-secret-key-for-jwt
JWT_ACCESS_EXPIRE=3600
JWT_REFRESH_EXPIRE=604800

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
```

## 🏃‍♂️ Running the Service

### Local Development Setup

For local development without AWS:

1. **Start PostgreSQL and Redis via Docker**

```bash
docker-compose up -d
```

2. **Run the application**

```bash
uvicorn main:app --reload
```

3. **Access the API documentation**

Open your browser to http://localhost:8000/docs to view and test the API.

### AWS Setup

For running with AWS services:

1. **Set up the SSH key for EC2 jump host access**

```bash
chmod 600 SmartUrl-KeyPair.pem
```

2. **Start the SSH tunnel to AWS services**

```bash
./tunnel.sh
```

This creates tunnels to:
- PostgreSQL: localhost:5432 → RDS instance
- Redis: localhost:6379 → ElastiCache instance

3. **Verify AWS connections**

```bash
python test_aws_connections.py
```

4. **Run the application**

```bash
uvicorn main:app --reload
```

5. **To close the tunnel when done**

```bash
pkill -f 'ssh -i.*smarturl'
```

## 🔨 AWS Architecture and Configuration

### AWS Services Used

1. **Amazon RDS for PostgreSQL**
   - Database service for URL and user data
   - Located in a private subnet for security
   - Access through EC2 jump host via SSH tunnel

2. **Amazon ElastiCache for Redis**
   - Caching service for improved performance
   - Reduces database load
   - Access through EC2 jump host via SSH tunnel

3. **Amazon S3**
   - Storage for QR code and barcode images
   - Public read access for serving images
   - Private write access with AWS credentials

4. **Amazon EC2**
   - Jump host for secure access to private services
   - Acts as a security gateway to RDS and ElastiCache
   - SSH key-based authentication

### Configuring AWS Services

#### RDS PostgreSQL Setup

1. Create an RDS PostgreSQL instance in the AWS Console:
   - Engine: PostgreSQL
   - Version: 13.4 or newer
   - Instance type: db.t3.micro (for development)
   - Storage: 20GB (minimum)
   - Multi-AZ: No (for development)
   - VPC: Private subnet with security group
   - Security Group: Allow inbound from EC2 jump host only

2. Initialize the database:
   - The application will create required tables at startup
   - Database schema documentation is in `documents/SmartUrl-database-schema.md`

#### ElastiCache Redis Setup

1. Create an ElastiCache Redis instance:
   - Engine: Redis
   - Version: 6.x or newer
   - Node type: cache.t3.micro (for development)
   - Number of nodes: 1 (for development)
   - VPC: Same VPC as RDS
   - Security Group: Allow inbound from EC2 jump host only

2. Configure Redis in `.env`:
   - When using tunnel: host=localhost
   - Set REDIS_SSL=false when using tunnel

#### S3 Bucket Setup

1. Create an S3 bucket:
   - Name: Choose a unique name
   - Region: Same as RDS/ElastiCache
   - Access: Block all public access
   - Versioning: Disabled (for development)

2. Configure bucket policy to allow read access:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

3. Set up CORS configuration:
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

4. Create an IAM user with S3 permissions:
   - Create a new IAM user for programmatic access
   - Attach policy: AmazonS3FullAccess
   - Save access key and secret for `.env` file

#### EC2 Jump Host Setup

1. Launch an EC2 instance:
   - Amazon Linux 2
   - t2.micro (for development)
   - VPC: Same as RDS/ElastiCache
   - Security Group: Allow SSH inbound (port 22) from your IP
   - Key Pair: Generate new or use existing (save as SmartUrl-KeyPair.pem)

2. Configure security groups:
   - EC2 Security Group: Allow SSH (port 22) from your IP
   - RDS Security Group: Allow PostgreSQL (port 5432) from EC2 Security Group
   - ElastiCache Security Group: Allow Redis (port 6379) from EC2 Security Group

### SSH Tunnel Setup

The `tunnel.sh` script creates SSH tunnels to access AWS services:

```bash
#!/bin/bash
ssh -i ./SmartUrl-KeyPair.pem \
    -L 5432:smarturl-postgres.cfai00ak63dx.eu-west-2.rds.amazonaws.com:5432 \
    -L 6379:smarturl-redis.ddr3jj.0001.euw2.cache.amazonaws.com:6379 \
    -N -f ec2-user@18.168.0.231
```

When running the tunnel:
1. Local port 5432 connects to your RDS instance
2. Local port 6379 connects to your ElastiCache instance
3. `-N` prevents executing remote commands
4. `-f` runs the tunnel in the background

## 📊 Development

### Authentication Configuration Explained

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
├── documents/
│   ├── SmartUrl-api.md              # API documentation
│   ├── SmartUrl-database-schema.md  # Database schema documentation
│   └── SmartUrl-Technical-Documentation.md # Comprehensive documentation
├── main.py                    # Application entry point
├── requirements.txt           # Project dependencies
├── .env                       # Environment variables
├── tunnel.sh                  # SSH tunnel script
├── test_aws_connections.py    # AWS connection tester
└── docker-compose.yml         # Docker services configuration
```

### Local Development with Docker

For local development with a PostgreSQL container instead of RDS:

```bash
# Use the local development docker-compose file
docker-compose -f docker-compose.dev.yml up -d
```

## Using the API

### Authentication

**Register a new user**:
```
POST /api/auth/register
{
  "email": "john@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Login**:
```
POST /api/auth/login
{
  "email": "john@example.com",
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
POST /api/urls/shorten
{
  "original_url": "https://example.com/your/long/url"
}
```

**Create QR code**:
```
POST /api/qr/create
{
  "content": "https://example.com/your/long/url"
}
```

**Create barcode**:
```
POST /api/barcode/create
{
  "content": "https://example.com/your/long/url",
  "barcode_type": "code128"
}
```

### Viewing History

**Get URL click history**:
```
GET /api/history/url/{short_code}?page=1&limit=20
```

**Get QR code scan history**:
```
GET /api/history/qr/{qr_id}?page=1&limit=20
```

**Get barcode scan history**:
```
GET /api/history/barcode/{barcode_id}?page=1&limit=20
```

**Get user history**:
```
GET /api/history/user/{user_id}?page=1&limit=20&resource_type=url
```

All history endpoints support the following parameters:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `start_date`: Filter by start date (ISO format)
- `end_date`: Filter by end date (ISO format)
- `resource_type`: Filter by resource type (url, qr, barcode)

## 🚢 Deployment

### Administrative Endpoints

The application provides several admin endpoints for maintenance:

**Sync click counts**:
```
POST /api/admin/sync-clicks
```

**Cache management**:
```
GET /api/admin/cache/stats
POST /api/admin/cache/clear/{prefix}
```

### Production Considerations

- Set up proper monitoring and logging
- Configure HTTPS with a valid SSL certificate
- Implement authentication for administrative endpoints
- Use managed services (AWS ECS/EKS) for container orchestration
- Set up CloudFront for content delivery
- Configure scheduled tasks for cache synchronization
- Implement proper database backup strategies

## 📚 Documentation

For comprehensive technical documentation, see:

- `documents/SmartUrl-Technical-Documentation.md` - Complete system documentation
- `documents/SmartUrl-api.md` - API documentation
- `documents/SmartUrl-database-schema.md` - Database schema documentation

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