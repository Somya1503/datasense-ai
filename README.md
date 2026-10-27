# DataSense AI 📊

**Turn raw data into meaningful insights with AI-powered data analysis.**

DataSense AI is a web application designed to help users analyze datasets and understand their data through a simple, accessible interface.

## 🌐 Live Demo

- **Live application:** https://datasense-ai-rosy.vercel.app/
- **GitHub repository:** https://github.com/Somya1503/datasense-ai
- **Backend health check:** https://datasense-ai-api-6ad6.onrender.com/health
- **Demo video:** *Add your demo video link here.*

## ✨ Features

- **Dataset upload:** Upload a CSV file for analysis.
- **Data analysis:** Send datasets to the backend for processing and analysis.
- **Results visualization:** Review the analysis results provided by the application.
- **Web-based interface:** Access the application through a modern web browser.
- **Deployed architecture:** A separately deployed frontend and backend.

*Add details about specific charts, AI-generated insights, supported file formats, or other features after verifying they are implemented.*

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | React |
| Frontend build tool | Vite |
| Backend | Python, FastAPI |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Version control | Git and GitHub |

## 🏗️ Architecture

DataSense AI uses a frontend-and-backend architecture.

1. The user interacts with the React frontend.
2. The frontend sends analysis requests to the FastAPI backend.
3. The backend processes the request and returns a response.
4. The frontend displays the results to the user.

## 🚀 Run Locally

### Prerequisites

- Node.js and npm
- Python 3
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Somya1503/datasense-ai.git
cd datasense-ai
```

### 2. Start the backend

Open a terminal in the project root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project's Python dependencies:

```bash
pip install -r requirements.txt
```

If the dependency file has a different name or location, use the one included in the repository.

Start the FastAPI server using the application's entry point. For example, if the application is defined in `main.py`:

```bash
uvicorn main:app --reload
```

The backend should be available at `http://127.0.0.1:8000`.

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create a `.env` file inside the `frontend` directory:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in your terminal, usually `http://localhost:5173`.

## ⚙️ Environment Configuration

The frontend uses the following environment variable:

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Base URL of the FastAPI backend |

For local development, use `http://127.0.0.1:8000`. For production, configure the deployed backend URL in the Vercel project settings.

The backend can configure allowed frontend origins using `CORS_ORIGINS`, as supported by its configuration.

**Security note:** Never commit passwords, API keys, access tokens, or other secrets. Frontend variables prefixed with `VITE_` are exposed to browser code and must not contain private credentials.

## 🧪 Testing

Before submitting the project, verify:

- The frontend starts successfully.
- The backend health endpoint responds.
- A valid CSV can be uploaded and analyzed.
- Results display correctly.
- Invalid input produces an appropriate error.
- The deployed frontend can communicate with the backend.

## 📹 Demo Video

The demo video should demonstrate:

1. Opening the live application.
2. Uploading a sample dataset.
3. Running the analysis.
4. Reviewing the resulting output.
5. Demonstrating error handling, where available.

**Demo link:** *Add your publicly accessible video link here.*

## 🔮 Future Improvements

Potential improvements include:

- Support for additional data formats.
- More interactive visualizations.
- Exporting analysis reports.
- Improved validation and error handling.
- Expanded analytical capabilities.

These are potential enhancements, not claims about existing functionality.

## 👩‍💻 Project Information

- **Project:** DataSense AI
- **Repository owner:** Somya1503
- **Repository:** [GitHub](https://github.com/Somya1503/datasense-ai)
- **Live application:** [Open DataSense AI](https://datasense-ai-rosy.vercel.app/)

## 📄 License

Add the appropriate license for your project before distributing or reusing the code. If no license has been selected, do not claim that the project is released under a particular open-source license.

