# Email Access Service

A Django + React application that connects to Gmail via Composio, pulls emails, stores them in a database, and displays them through an API and UI.

## Architecture

```
Gmail → Composio (OAuth + Triggers) → Django Webhook → SQLite → REST API → React UI
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- A [Composio](https://composio.dev) account

## Setup Instructions

### 1. Clone & Install Dependencies

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ../requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Create Composio Auth Config

1. Go to [Composio Dashboard](https://app.composio.dev)
2. Navigate to **Auth Configs** → **Create Auth Config**
3. Select **Gmail** toolkit
4. Choose **OAuth2** authentication
5. Configure scopes (gmail.readonly, gmail.modify)
6. Click **Create** and copy the **Auth Config ID**

### 3. Get Composio API Key

1. Go to [Composio Settings](https://app.composio.dev/settings)
2. Copy your **API Key**

### 4. Configure Environment

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp ../env.example .env
```

Edit `.env` with your values:

```env
COMPOSIO_API_KEY=your_api_key_here
COMPOSIO_AUTH_CONFIG_ID=your_auth_config_id_here
DJANGO_SECRET_KEY=generate-a-random-secret-key
DEBUG=True
WEBHOOK_BASE_URL=http://localhost:8000
```

> **Tip:** Generate a Django secret key:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(50))"
> ```

### 5. Initialize Database

```bash
cd backend
source venv/bin/activate
python manage.py migrate
```

### 6. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 7. Connect Gmail

1. Open http://localhost:5173
2. Click **Connect Gmail**
3. Complete Google OAuth in the popup
4. Get your `connected_account_id` from Composio:
   ```bash
   # In backend directory with venv activated
   python -c "
   from composio import Composio
   import os
   from dotenv import load_dotenv
   load_dotenv()
   c = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
   entity = c.get_entity('default-user')
   conn = entity.get_connection(app='gmail')
   print(f'Connected Account ID: {conn.id}')
   "
   ```
5. Click **Complete Connection** and paste the ID
6. Click **Sync** to fetch emails

## For Real-Time Webhooks (Optional)

To receive new emails automatically, Composio needs to reach your webhook. Use ngrok:

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Expose local server
ngrok http 8000

# Update .env with the ngrok URL
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
```

Then restart the backend and re-complete the connection.

## Project Structure

```
email-access/
├── backend/
│   ├── email_service/       # Django project settings
│   │   ├── settings.py      # Configuration (reads from .env)
│   │   └── urls.py          # Root URL routing
│   ├── emails/              # Main Django app
│   │   ├── models.py        # Email, ComposioConnection models
│   │   ├── views.py         # API endpoints
│   │   ├── services.py      # Composio integration logic
│   │   ├── serializers.py   # DRF serializers
│   │   └── urls.py          # App URL routing
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── api.js           # API client
│   │   └── App.css          # Styles
│   └── package.json
├── requirements.txt         # Python dependencies
├── env.example              # Example environment file
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/emails/` | GET | List emails (paginated) |
| `/api/emails/{id}/` | GET | Get single email |
| `/api/emails/{id}/mark_read/` | POST | Mark email as read |
| `/api/emails/stats/` | GET | Get email counts |
| `/api/connect/` | POST | Start Gmail OAuth |
| `/api/connect/complete/` | POST | Complete connection |
| `/api/connect/status/` | GET | Check connection status |
| `/api/sync/` | POST | Fetch emails from Gmail |
| `/api/webhook/email/` | POST | Webhook for new emails |

## How It Works

1. **OAuth Flow**: User connects Gmail via Composio's managed OAuth
2. **Trigger Setup**: After connection, we enable `GMAIL_NEW_GMAIL_MESSAGE` trigger
3. **Email Sync**: Click "Sync" to fetch emails via Composio's Gmail tools
4. **Storage**: Emails stored in SQLite with proper HTML detection
5. **Display**: React frontend renders emails with Gmail-like UI

## Troubleshooting

**"COMPOSIO_API_KEY is not set"**
- Make sure you created `.env` file in the `backend/` directory
- Check that the file has `COMPOSIO_API_KEY=your_key`

**"No active connection found"**
- Complete the Gmail OAuth flow first
- Make sure to click "Complete Connection" after authorizing

**Emails show as raw HTML**
- Re-sync emails after the latest code update
- The parsing logic now correctly detects HTML content

## License

MIT
