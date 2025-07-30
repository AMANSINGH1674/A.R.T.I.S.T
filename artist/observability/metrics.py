"""
Metrics collection and Prometheus integration.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
import structlog
from typing import Dict, Any
import time
from functools import wraps

logger = structlog.get_logger()

# Create a custom registry
registry = CollectorRegistry()

# Define metrics
workflow_executions_total = Counter(
    'artist_workflow_executions_total',
    'Total number of workflow executions',
    ['workflow_id', 'status', 'user_id'],
    registry=registry
)

workflow_duration_seconds = Histogram(
    'artist_workflow_duration_seconds',
    'Time spent executing workflows',
    ['workflow_id'],
    registry=registry
)

agent_executions_total = Counter(
    'artist_agent_executions_total',
    'Total number of agent executions',
    ['agent_name', 'status'],
    registry=registry
)

agent_duration_seconds = Histogram(
    'artist_agent_duration_seconds',
    'Time spent executing agents',
    ['agent_name'],
    registry=registry
)

tool_executions_total = Counter(
    'artist_tool_executions_total',
    'Total number of tool executions',
    ['tool_name', 'status'],
    registry=registry
)

tool_duration_seconds = Histogram(
    'artist_tool_duration_seconds',
    'Time spent executing tools',
    ['tool_name'],
    registry=registry
)

active_workflows = Gauge(
    'artist_active_workflows',
    'Number of currently active workflows',
    registry=registry
)

feedback_submissions_total = Counter(
    'artist_feedback_submissions_total',
    'Total number of feedback submissions',
    ['feedback_type', 'rating'],
    registry=registry
)

rlhf_training_cycles_total = Counter(
    'artist_rlhf_training_cycles_total',
    'Total number of RLHF training cycles',
    ['training_type', 'status'],
    registry=registry
)

# System info
system_info = Info(
    'artist_system_info',
    'ARTIST system information',
    registry=registry
)

# Set system info
system_info.info({
    'version': '1.0.0',
    'python_version': '3.11',
    'environment': 'production'
})


class MetricsCollector:
    """Centralized metrics collection"""

    @staticmethod
    def record_workflow_execution(workflow_id: str, status: str, user_id: str, duration: float):
        """Record workflow execution metrics"""
        workflow_executions_total.labels(
            workflow_id=workflow_id,
            status=status,
            user_id=user_id
        ).inc()
        
        workflow_duration_seconds.labels(workflow_id=workflow_id).observe(duration)
        logger.info("Recorded workflow metrics", 
                   workflow_id=workflow_id, 
                   status=status, 
                   duration=duration)

    @staticmethod
    def record_agent_execution(agent_name: str, status: str, duration: float):
        """Record agent execution metrics"""
        agent_executions_total.labels(
            agent_name=agent_name,
            status=status
        ).inc()
        
        agent_duration_seconds.labels(agent_name=agent_name).observe(duration)
        logger.debug("Recorded agent metrics", 
                    agent_name=agent_name, 
                    status=status, 
                    duration=duration)

    @staticmethod
    def record_tool_execution(tool_name: str, status: str, duration: float):
        """Record tool execution metrics"""
        tool_executions_total.labels(
            tool_name=tool_name,
            status=status
        ).inc()
        
        tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
        logger.debug("Recorded tool metrics", 
                    tool_name=tool_name, 
                    status=status, 
                    duration=duration)

    @staticmethod
    def increment_active_workflows():
        """Increment active workflows counter"""
        active_workflows.inc()

    @staticmethod
    def decrement_active_workflows():
        """Decrement active workflows counter"""
        active_workflows.dec()

    @staticmethod
    def record_feedback_submission(feedback_type: str, rating: str = "none"):
        """Record feedback submission"""
        feedback_submissions_total.labels(
            feedback_type=feedback_type,
            rating=rating
        ).inc()
        logger.info("Recorded feedback metrics", 
                   feedback_type=feedback_type, 
                   rating=rating)

    @staticmethod
    def record_rlhf_training(training_type: str, status: str):
        """Record RLHF training metrics"""
        rlhf_training_cycles_total.labels(
            training_type=training_type,
            status=status
        ).inc()
        logger.info("Recorded RLHF training metrics", 
                   training_type=training_type, 
                   status=status)

    @staticmethod
    def get_metrics():
        """Get current metrics in Prometheus format"""
        return generate_latest(registry)


def measure_execution_time(metric_type: str, name: str):
    """Decorator to measure execution time"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                raise
            finally:
                duration = time.time() - start_time
                
                if metric_type == "workflow":
                    MetricsCollector.record_workflow_execution(name, status, "unknown", duration)
                elif metric_type == "agent":
                    MetricsCollector.record_agent_execution(name, status, duration)
                elif metric_type == "tool":
                    MetricsCollector.record_tool_execution(name, status, duration)
        
        return wrapper
    return decorator
