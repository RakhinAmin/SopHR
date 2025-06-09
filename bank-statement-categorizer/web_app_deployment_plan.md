# Transaction Categorizer – Web App Deployment & Production Plan

## 1. Web Application Infrastructure

### Architecture
- **Frontend**: 
  - Streamlit (recommended for MVP and internal tools), or 
  - Flask/FastAPI + HTML/JS for full UI control
- **Backend Logic**: Python-based fuzzy categorization using RapidFuzz
- **File Handling**: 
  - Upload CSV → Process → Display categorized output → Enable download
- **Hosting Options**:
  - Streamlit Cloud (fastest for internal tools)
  - Render or Heroku (Flask/FastAPI)
  - Azure App Service or AWS Elastic Beanstalk (enterprise options)

## 2. Deployment Strategy

### CI/CD Pipeline (Optional for MVP)
```
GitHub → Test → Build → Deploy to Host
```

### Streamlit Deployment Flow
1. Push your code to a GitHub repository
2. Go to https://streamlit.io/cloud
3. Connect your repository and deploy
4. Set environment variables if needed via the platform dashboard

### Flask/FastAPI Deployment Flow
1. Wrap categorizer in API endpoints
2. Create HTML upload interface (or use Streamlit for UI)
3. Deploy to:
   - Render (using `render.yaml`)
   - Heroku (using `Procfile`)
   - Railway (simple Flask deployments)

## 3. Security and Access

| Area             | Implementation                          |
|------------------|------------------------------------------|
| HTTPS            | Enabled by hosting platform              |
| File Validation  | Accept only `.csv`, limit file size      |
| Input Sanitation | Clean invalid characters and scripts     |
| Authentication   | Optional: OAuth2, email login, or password-protected access

## 4. Application Features

- CSV file upload
- Fuzzy matching using rule set (RapidFuzz)
- Adjustable threshold for matching (slider or input)
- Categorized output display (in table format)
- CSV download of results
- Suggestions when multiple categories match

## 5. Monitoring and Logging

- Use built-in logs from Streamlit/Render/Heroku dashboards
- Add Python logging (`logging` module)
- Optional integration with:
  - Sentry (error tracking)
  - UptimeRobot or BetterStack (uptime monitoring)

## 6. Maintenance and Support

| Activity                   | Frequency         |
|----------------------------|-------------------|
| Rule Set Updates           | As needed         |
| Bug Fixes and Improvements | As needed         |
| Dependency Updates         | Monthly           |
| Security Patches           | Monthly or urgent |

## 7. Go-Live Timeline

| Week | Milestone                                  |
|------|---------------------------------------------|
| 1    | Finalize UI and integrate categorizer logic |
| 2    | Implement file upload and download features |
| 3    | Deploy to cloud hosting (Streamlit or Flask)|
| 4    | Test, log, and error-handle the system      |
| 5    | Official release and collect feedback       |

## 8. Project Structure

```
project/
│
├── app.py                # Main app logic (Streamlit or Flask)
├── categorize.py         # Fuzzy categorization logic
├── rules.csv             # Matching rule set
├── requirements.txt      # Dependencies
└── README.md             # Documentation
```

## 9. Technology Stack

- Python 3.8+
- Streamlit or Flask/FastAPI
- RapidFuzz
- Pandas
- Docker (optional)
- GitHub (for CI/CD and versioning)