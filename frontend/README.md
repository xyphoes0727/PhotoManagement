# Photo Management Frontend

A React + JavaScript frontend for the Photo Management application with AI-powered features.

## Features

- 📤 **Photo Upload** - Drag & drop or browse to upload multiple photos
- 🔍 **AI Search** - Natural language search for photos using text queries
- 🖼️ **Gallery View** - Browse photos in grid or list layout with filters
- 📁 **Albums** - Create and manage photo albums with AI suggestions
- 👤 **Face Detection** - Automatic face detection in uploaded photos
- 🏷️ **Auto Captioning** - AI-generated captions for your photos

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Backend server running on `http://localhost:9000`

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The app will be available at `http://localhost:3000`

## Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── manifest.json
├── src/
│   ├── components/
│   │   ├── Header/
│   │   ├── Layout/
│   │   └── Sidebar/
│   ├── pages/
│   │   ├── Albums.js
│   │   ├── Dashboard.js
│   │   ├── Gallery.js
│   │   ├── Search.js
│   │   └── Upload.js
│   ├── services/
│   │   └── api.js
│   ├── App.js
│   ├── App.css
│   ├── index.js
│   └── index.css
└── package.json
```

## API Integration

The frontend communicates with the Django backend through the following endpoints:

- `POST /api/query/` - Search photos using natural language
- `POST /api/upload/` - Upload and process photos
- `POST /api/caption/` - Get AI-generated captions
- `POST /api/face/` - Detect faces in photos
- `POST /api/albumization/` - Get album suggestions

## Environment Variables

Create a `.env` file in the frontend directory:

```
REACT_APP_API_URL=http://localhost:9000
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

## Technologies Used

- React 18
- React Router DOM
- Axios (HTTP client)
- Lucide React (Icons)
- CSS Variables for theming
