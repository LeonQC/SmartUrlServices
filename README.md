# SmartUrl

> A modern URL shortening and QR code generation service built with FastAPI and PostgreSQL.

SmartUrl provides a robust API for creating short URLs, QR codes, and barcodes with built-in analytics. The service is designed for scalability, using AWS S3 for image storage and AWS RDS for database management.

## 🚀 Features

- **URL Shortening** - Convert long URLs to compact, shareable links
- **QR Code Generation** - Create scannable QR codes for any URL
- **Barcode Creation** - Generate barcodes linked to destinations
- **User Registration** - Create accounts to manage your resources
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
```

4. **Start Redis via Docker**

```bash
docker-compose up -d
```

5. **Run the application**

```bash
python main.py
```

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

### Project Structure

```
smarturl/
├── app/
│   ├── api/
│   │   ├── auth_routes.py     # User registration routes
│   │   └── url_routes.py      # URL, QR code, and barcode routes
│   ├── models/
│   │   ├── url_schemas.py     # URL-related schemas
│   │   └── user_schema.py     # User-related schemas
│   ├── services/
│   │   ├── url_service.py     # URL shortening service
│   │   ├── qr_service.py      # QR code generation service
│   │   ├── barcode_service.py # Barcode generation service
│   │   └── s3_service.py      # AWS S3 integration service
│   ├── database/
│   │   ├── url_db.py          # URL-related database operations
│   │   └── user_db.py         # User-related database operations
│   └── cache/
│       └── redis_client.py    # Redis caching functionality
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

## 🚢 Deployment

### Production Considerations

- Set up proper monitoring and logging
- Configure HTTPS with a valid SSL certificate
- Implement authentication for administrative endpoints
- Use managed services (AWS ECS/EKS) for container orchestration
- Set up CloudFront for content delivery

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)
- [AWS](https://aws.amazon.com/)

