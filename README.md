# SmartUrl Backend

SmartUrl is a simple yet powerful URL management platform that helps convert long URLs into compact, easy-to-share links, QR codes, and barcodes. The project supports automatic website title extraction, comprehensive analytics, and user-based resource management, allowing you to track and optimize the performance of all your shared links.

## Features

### Current Features

- **URL Shortening**: Convert long URLs into short, manageable links
- **Click Tracking**: Monitor how many times each short link has been accessed
- **QR Code Generation**: Create QR codes from your URLs
- **Barcode Generation**: Generate barcodes for your URLs
- **Scan Tracking**: Monitor how many times each QR code and barcode has been scanned
- **Title Extraction**: Automatically extract and display the title of the target website for all resources (URLs, QR codes, and barcodes)
- **Info Endpoints**: Get statistics about your shortened URLs, QR codes, and barcodes
- **Redis Caching**: Improved performance with in-memory caching for all resources (URLs, QR codes, and barcodes)
- **Counter Batching**: Efficient counter updates with Redis (reduces database writes)
- **Rate Limiting**: Protection against API abuse with Redis-based rate limiting
- **Dockerized Environment**: Easy setup with containerized services

### Planned Features

- **User Authentication**: Create an account and manage your links
- **Advanced Analytics**: Get detailed stats about link usage
- **Personalized Dashboards**: View statistics for all your shortened URLs, QR codes, and barcodes in one place
- **History Pages**: View paginated history of all resources you've created
- **Resource Management**: Ability to delete or edit your created resources
- **Visual Analytics**: Charts and graphs showing usage patterns over time
- **Export Capabilities**: Download your analytics data in various formats

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/tonyx1998/smarturl.git
   cd smarturl
   ```

2. **Set up a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Docker services**

   Create a `docker-compose.yml` file in your project root:

   ```yaml
   version: '3.8'

   services:
     # PostgreSQL Database
     postgres:
       image: postgres:15-alpine
       container_name: smarturl-postgres
       environment:
         - POSTGRES_USER=postgres
         - POSTGRES_PASSWORD=postgres
         - POSTGRES_DB=smarturl
       ports:
         - "5432:5432"
       volumes:
         - postgres_data:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U postgres"]
         interval: 5s
         timeout: 5s
         retries: 5

     # Redis Cache
     redis:
       image: redis:alpine
       container_name: smarturl-redis
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       command: redis-server --appendonly yes
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 5s
         retries: 5
         
     # pgAdmin for PostgreSQL management
     pgadmin:
       image: dpage/pgadmin4
       container_name: smarturl-pgadmin
       environment:
         - PGADMIN_DEFAULT_EMAIL=admin@example.com
         - PGADMIN_DEFAULT_PASSWORD=adminpassword
       ports:
         - "5050:80"
       depends_on:
         - postgres

   volumes:
     postgres_data:
     redis_data:
   ```

5. **Create a `.env` file**

   ```
   DB_NAME=smarturl
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_TTL=3600
   ```

6. **Start Docker services**

   ```bash
   docker-compose up -d
   ```

7. **Run the application**

   ```bash
   python main.py
   ```

8. **Access the application**
   - Web interface: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - pgAdmin: http://localhost:5050 (login with admin@example.com/adminpassword)

## Project Structure

```
/SmartUrlServices/
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (not in version control)
├── docker-compose.yml      # Docker services configuration
├── static/                 # Static files directory
│   ├── qrcodes/            # Generated QR code images
│   └── barcodes/           # Generated barcode images
├── app/
│   ├── __init__.py         # Makes app a package
│   ├── api/
│   │   ├── __init__.py     # Makes api a package
│   │   └── routes.py       # API endpoint definitions
│   ├── models/
│   │   ├── __init__.py     # Makes models a package
│   │   └── schemas.py      # Pydantic data models
│   ├── services/
│   │   ├── __init__.py     # Makes services a package
│   │   ├── url_service.py  # URL shortener business logic
│   │   ├── qr_service.py   # QR code generator business logic
│   │   └── barcode_service.py # Barcode generator business logic
│   ├── database/
│   │   ├── __init__.py     # Makes database a package
│   │   └── db.py           # Database operations
│   └── cache/
│       ├── __init__.py     # Makes cache a package
│       └── redis_client.py # Redis connection and caching functions
```

## Performance Optimization

The application uses several techniques for performance optimization:

1. **Redis Caching**: Popular short URLs, QR codes, and barcodes are cached in Redis to reduce database lookups.
2. **Counter Batching**: Click and scan counts are aggregated in Redis and updated in the database periodically (every 10 increments) to reduce database writes.
3. **Info Caching**: Frequently requested information about resources is cached to improve response times.
4. **Rate Limiting**: API endpoints are protected against abuse with SlowAPI-based rate limiting, enforcing limits of 10 requests per minute for resource creation endpoints.

### Rate Limiting Implementation

The application uses the SlowAPI library to provide tiered rate limiting:

- **Tier 1: Resource Creation** (10 requests per minute)
  - `/shorten/`: Create short URLs
  - `/qrcode/`: Create QR codes
  - `/barcode/`: Create barcodes
  
- **Tier 2: Resource Information** (60 requests per minute)
  - `/info/{short_code}`: Get short URL information
  - `/qrcode/info/{qr_code_id}`: Get QR code information
  - `/barcode/info/{barcode_id}`: Get barcode information
  
- **Tier 3: User-Facing Endpoints** (No rate limiting)
  - `/{short_code}`: Redirect from short URLs
  - `/qrcode/{qr_code_id}`: Redirect from QR codes
  - `/barcode/{barcode_id}`: Redirect from barcodes
  - `/qrcode/{qr_code_id}/image`: Get QR code images
  - `/barcode/{barcode_id}/image`: Get barcode images

This tiered approach protects resource-intensive operations while ensuring high availability for end-user experiences. Rate limits are applied per IP address.

## Website Title Extraction

SmartUrl automatically extracts the title of the target website when creating URLs, QR codes, or barcodes:

### How It Works

1. When a user submits a URL for shortening, QR code, or barcode generation, the service makes a request to the target website.
2. The HTML response is parsed using BeautifulSoup to extract the content of the `<title>` tag.
3. This title is stored in the database and returned in API responses for better context.
4. The title is displayed in the history and information views, making it easier to identify resources.

### Implementation Details

- A custom User-Agent header is used to prevent being blocked by websites
- Requests have a 5-second timeout to prevent long processing times
- Error handling ensures the service works even if title extraction fails
- If extraction fails (network issues, invalid URL, missing title tag), the title field will be null
- No additional input is required from users for this feature

### Redis Key Patterns

The application uses the following Redis key patterns:

- **URL Keys**:
  - `url:{short_code}` - The original URL for a short link
  - `info:{short_code}` - Full information about a short URL
  - `clicks:{short_code}` - Click counter for a short URL

- **QR Code Keys**:
  - `qrcode:{qr_code_id}` - The original URL for a QR code
  - `qrinfo:{qr_code_id}` - Full information about a QR code
  - `qrscans:{qr_code_id}` - Scan counter for a QR code

- **Barcode Keys**:
  - `barcode:{barcode_id}` - The original URL for a barcode
  - `barinfo:{barcode_id}` - Full information about a barcode
  - `barscans:{barcode_id}` - Scan counter for a barcode

- **Rate Limiting Keys**:
  - `ratelimit:{key}` - Rate limit counters for API endpoints

## API Endpoints

### URL Shortener Endpoints

- **POST /shorten/**: Create a new short URL
- **GET /{short_code}**: Redirect to the original URL
- **GET /info/{short_code}**: Get information about a short URL

### QR Code Endpoints

- **POST /qrcode/**: Create a new QR code
- **GET /qrcode/{qr_code_id}/image**: Get the QR code image
- **GET /qrcode/{qr_code_id}**: Redirect to the original URL
- **GET /qrcode/info/{qr_code_id}**: Get information about a QR code

### Barcode Endpoints

- **POST /barcode/**: Create a new barcode
- **GET /barcode/{barcode_id}/image**: Get the barcode image
- **GET /barcode/{barcode_id}**: Redirect to the original URL
- **GET /barcode/info/{barcode_id}**: Get information about a barcode

## Working with pgAdmin

After starting the Docker services, you can access pgAdmin at http://localhost:5050:

1. Login with email: admin@example.com and password: adminpassword
2. Add a new server with these connection details:
   - Host: postgres
   - Port: 5432
   - Username: postgres
   - Password: postgres
   - Database: smarturl

## Redis Cache Management

To monitor and manage the Redis cache:

1. Access the Redis CLI within the Docker container:
   ```bash
   docker exec -it smarturl-redis redis-cli
   ```

2. View all cache keys:
   ```bash
   KEYS *
   ```

3. View a specific cached value:
   ```bash
   GET url:abc123
   ```

4. Clear the entire cache if needed:
   ```bash
   FLUSHALL
   ```

5. Get stats about current Redis memory usage:
   ```bash
   INFO memory
   ```

## Troubleshooting

### PostgreSQL Connection Issues

If you have a local PostgreSQL instance running, you may encounter port conflicts. You can either:
- Stop your local PostgreSQL service, or
- Change the port in docker-compose.yml to use a different port (e.g., 5433) and update your .env file accordingly

### Redis Connection Issues

If Redis fails to connect, check:
- If you have a local Redis instance running on port 6379
- Update your .env and docker-compose.yml to use a different port if needed
- Verify with `docker-compose ps` that the Redis container is running
- Try connecting manually: `docker exec -it smarturl-redis redis-cli ping`

### Docker Issues

If containers fail to start:
- Ensure Docker Desktop is running
- Check container logs: `docker-compose logs`
- Verify ports are not in use by other services
- Try restarting the containers: `docker-compose restart`

### Image Generation Issues

If QR code or barcode images are not generating:
- Ensure the static directories have proper permissions
- Check for Python library dependencies (Pillow, qrcode, python-barcode, cairosvg)
- Inspect the logs for any file system related errors
