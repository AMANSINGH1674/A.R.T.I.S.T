# ARTIST: Agentic Tool-Integrated Large Language Model

This repository contains the source code for the **ARTIST (Agentic Tool-Integrated LLM)** project, an enterprise-grade AI system designed to autonomously plan, reason, and execute complex, multi-step workflows.

ARTIST empowers LLM-powered agents to transcend text generation by dynamically selecting and interfacing with external tools and APIs. The system is designed to deliver end-to-end, auditable, and actionable automation at scale—not just providing answers, but accomplishing tasks, delivering insights, and driving real-world outcomes.

## ✨ Features

- 🧠 **RLHF-Based Learning Engine**: Continuously improves with user feedback through a comprehensive Reinforcement Learning from Human Feedback (RLHF) system.
- 🚀 **Asynchronous Workflow Execution**: Handles long-running tasks efficiently with Celery, ensuring a responsive and non-blocking user experience.
- 🔐 **Enterprise-Grade Security**: Features a robust security layer with JWT-based authentication, Role-Based Access Control (RBAC), prompt injection filters, and a secure code execution sandbox.
- 📊 **Comprehensive Observability**: Provides deep insights into the system's performance with LangSmith tracing, Prometheus metrics, and Grafana dashboards.
- 🗄️ **Production-Ready Database**: Utilizes PostgreSQL for robust data persistence and includes Alembic for managing database schema migrations.
- 🌐 **Web-Based UI**: Offers a user-friendly interface for executing workflows, monitoring their status, and viewing the results.
- 🔌 **Extensible Tooling & Agents**: Easily extend the system with new tools and agents through a dynamic registration system.
- 🐳 **Containerized Deployment**: Comes with Docker and Kubernetes configurations for easy and scalable deployment in any environment.

## 🚀 Getting Started

This section will guide you through setting up and running the ARTIST application on your local machine.

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- An OpenAI API key (or another LLM provider)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd A.R.T.I.S.T-2
```

### 2. Set Up the Environment

Use the setup script to create a virtual environment, install dependencies, and set up the database:

```bash
chmod +x scripts/setup.py
./scripts/setup.py --full
```

This will:
- Create and activate a Python virtual environment.
- Install all required dependencies.
- Create the database tables.
- Start the required Docker containers (PostgreSQL, Redis, Milvus).

### 3. Configure Environment Variables

Copy the example environment file and update it with your configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with your API keys and other settings:

```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=a_very_secure_secret_key
# ... other settings
```

### 4. Run the Application

```bash
python -m artist.main
```

The application will be available at `http://localhost:8000`. You can view the API documentation at `http://localhost:8000/docs` and the web UI at `http://localhost:8000/static/index.html`.

## 📚 Documentation

For more detailed information, please refer to the documentation in the `docs` directory:

- **[API Documentation](docs/api_documentation.md)**: Detailed information about the API endpoints.
- **[User Guide](docs/user_guide.md)**: Instructions for end-users on how to use the system.
- **[Developer Guide](docs/developer_guide.md)**: Instructions for developers on how to extend the system.
- **[Deployment Guide](docs/deployment_guide.md)**: Instructions for deploying the system in different environments.

## 🔌 API Usage

### Authentication

First, obtain a JWT token by logging in:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "password": "password"
  }'
```

### Execute a Workflow

Use the token to execute a workflow:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/workflow/execute' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_request": "Research the latest trends in AI and provide a comprehensive summary.",
    "workflow_id": "default"
  }'
```

### Monitor Workflow Status

Check the status of your workflow using the returned task ID:

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/workflow/status/{task_id}'
```

### Submit Feedback

Provide feedback to improve the system:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/rlhf/feedback' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_id": "default",
    "run_id": "task_id_here",
    "feedback_type": "rating",
    "rating": 5
  }'
```

## 🚀 Production Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Check status
docker-compose ps
```

### Kubernetes Deployment

```bash
# Create secrets
kubectl create secret generic artist-secrets \
  --from-literal=database-url="postgresql://user:password@host:5432/artist" \
  --from-literal=openai-api-key="your-openai-key"

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /api/v1/monitoring/metrics` (Prometheus format)
- **Grafana Dashboard**: Import `grafana/artist-dashboard.json`

## 🧪 Testing

Run the test suite to ensure everything is working correctly:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=artist --cov-report=html
```

### Test Results

All tests are currently passing. For detailed test results, please see the `test_results.log` file.

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/A.R.T.I.S.T-2.git
cd A.R.T.I.S.T-2

# Set up development environment
./scripts/setup.py --env-only
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install black isort flake8 mypy

# Run formatting and linting
black artist/
isort artist/
flake8 artist/
mypy artist/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/yourorg/A.R.T.I.S.T-2/issues)
3. Create a new issue if needed
4. Join our community discussions

## 🙏 Acknowledgments

- Built with [LangChain](https://github.com/hwchase17/langchain) and [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [FastAPI](https://fastapi.tiangolo.com/)
- Monitoring with [Prometheus](https://prometheus.io/) and [Grafana](https://grafana.com/)
- Vector database support via [Milvus](https://milvus.io/)

## Project Structure

- `artist/`: Core application source code.
  - `api/`: FastAPI application, endpoints, and utilities.
  - `core/`: Core components like registries and logging.
  - `database/`: Database models and session management.
  - `knowledge/`: RAG and knowledge base components.
  - `observability/`: Monitoring and tracing components.
  - `orchestration/`: Workflow orchestration using LangGraph.
  - `rlhf/`: RLHF-based learning engine.
  - `security/`: Security features, authentication, and access control.
  - `tools/`: External tool and API integrations.
  - `worker/`: Celery worker and tasks.
  - `main.py`: Main application entry point.
- `docs/`: Comprehensive documentation.
- `k8s/`: Kubernetes deployment configurations.
- `migrations/`: Alembic database migrations.
- `static/`: Web UI files.
- `tests/`: Unit and integration tests.
- `Dockerfile.prod`: Production-ready Dockerfile.
- `docker-compose.yml`: Docker Compose setup for all services.
- `requirements.txt`: Python dependencies.

