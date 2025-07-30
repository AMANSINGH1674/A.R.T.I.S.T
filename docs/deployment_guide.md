# ARTIST Deployment Guide

This guide provides instructions for deploying the ARTIST system in different environments.

## Prerequisites

Before deploying ARTIST, ensure you have the following:

- Docker and Docker Compose
- PostgreSQL database
- Redis instance
- Milvus vector database
- API keys for LLM providers (OpenAI, Anthropic)

## Local Development Deployment

For local development, use Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd A.R.T.I.S.T-2

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Start all services
docker-compose up --build
```

The application will be available at `http://localhost:8000`.

## Production Deployment

### Kubernetes Deployment

1. **Prepare secrets:**
   ```bash
   kubectl create secret generic artist-secrets \
     --from-literal=database-url="postgresql://user:password@host:5432/artist" \
     --from-literal=openai-api-key="your-openai-key"
   ```

2. **Deploy the application:**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

3. **Set up ingress (optional):**
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

### Docker Swarm Deployment

1. **Initialize swarm:**
   ```bash
   docker swarm init
   ```

2. **Deploy stack:**
   ```bash
   docker stack deploy -c docker-compose.prod.yml artist
   ```

## Configuration

### Environment Variables

Key environment variables to configure:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key
- `SECRET_KEY`: JWT secret key (generate a secure random string)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

### Database Setup

1. Create database tables:
   ```bash
   python -c "from artist.database.session import create_all_tables; create_all_tables()"
   ```

2. Run migrations (if using Alembic):
   ```bash
   alembic upgrade head
   ```

### Monitoring Setup

1. **Prometheus**: Configure Prometheus to scrape metrics from `/api/v1/monitoring/metrics`
2. **Grafana**: Import the dashboard from `grafana/artist-dashboard.json`
3. **LangSmith**: Set `LANGSMITH_API_KEY` for tracing

## Security Considerations

- Use HTTPS in production
- Rotate JWT secret keys regularly
- Configure firewall rules to restrict access
- Use secure database passwords
- Enable authentication on Redis and Milvus
- Regular security updates

## Scaling

### Horizontal Scaling

- Scale API servers: Increase replica count in Kubernetes
- Scale workers: Increase Celery worker replicas
- Scale databases: Use read replicas for PostgreSQL

### Vertical Scaling

- Increase CPU/memory limits in Kubernetes
- Optimize database queries and indexing
- Use connection pooling

## Troubleshooting

### Common Issues

1. **Database connection failures**: Check connection string and network connectivity
2. **Redis connection issues**: Verify Redis is running and accessible
3. **LLM API failures**: Check API keys and rate limits
4. **Memory issues**: Increase memory limits for containers

### Logs

View logs using:
```bash
kubectl logs -f deployment/artist-api
docker logs artist_app_1
```

## Backup and Recovery

### Database Backup

```bash
pg_dump -h host -U user -d artist > backup.sql
```

### Configuration Backup

Backup environment variables and Kubernetes secrets regularly.
