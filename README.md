# SmartUrl Backend

SmartUrl is a simple yet powerful URL management platform that helps convert long URLs into compact, easy-to-share links, QR codes, and barcodes. The project supports automatic website title extraction, comprehensive analytics, and user-based resource management, allowing you to track and optimize the performance of all your shared links.

## Features

### Current Features

- **URL Shortening**: Convert long URLs into short, manageable links
- **Click Tracking**: Monitor how many times each short link has been accessed
- **Title Extraction**: Automatically extract and display the title of the target website
- **Info Endpoint**: Get statistics about your shortened URLs

### Planned Features

- **User Authentication**: Create an account and manage your links
- **QR Code Generation**: Create QR codes from your URLs
- **Barcode Generation**: Generate barcodes for your URLs
- **Advanced Analytics**: Get detailed stats about link usage
- **Personalized Dashboards**: View statistics for all your shortened URLs, QR codes, and barcodes in one place
- **History Pages**: View paginated history of all resources you've created
- **Resource Management**: Ability to delete or edit your created resources
- **Visual Analytics**: Charts and graphs showing usage patterns over time
- **Export Capabilities**: Download your analytics data in various formats

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL database
- pip (Python package manager)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/smarturl.git
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

4. **Set up the PostgreSQL database**

   ```bash
   # First, make sure PostgreSQL is installed and running
   createdb url_shortener
   ```

5. **Create a .env file**

   ```
   DB_NAME=url_shortener
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   ```

6. **Run the application**

   ```bash
   python main.py
   ```

7. **Access the application**
   - Web interface: http://localhost:8000
   - API documentation: http://localhost:8000/docs

## Project Structure

```
/smarturl/
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies
├── .env                    # Environment variables (not in version control)
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
│   │   └── url_service.py  # Business logic
│   └── database/
│       ├── __init__.py     # Makes database a package
│       └── db.py           # Database operations
```

## Title Extraction

The application automatically attempts to extract the title from the target website when creating a short URL:

1. When a URL is submitted, the system makes a request to the target webpage
2. It parses the HTML content to extract the `<title>` tag
3. The title is stored in the database along with the URL
4. The title is included in API responses for better context

If the title can't be extracted (due to connection issues, invalid URL, or missing title tag), the title field will be null.
