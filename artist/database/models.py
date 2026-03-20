"""
Database models for ARTIST application.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    roles = Column(JSON, default=list)  # Store roles as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workflows = relationship("WorkflowExecution", back_populates="user")

class WorkflowDefinition(Base):
    """Workflow definition model"""
    __tablename__ = "workflow_definitions"
    
    id = Column(String(100), primary_key=True, index=True)  # workflow_id
    name = Column(String(255), nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)  # Store workflow graph as JSON
    version = Column(String(50), default="1.0.0")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow_definition")

class WorkflowExecution(Base):
    """Workflow execution model"""
    __tablename__ = "workflow_executions"
    
    id = Column(String(100), primary_key=True, index=True)  # run_id
    task_id = Column(String(100), unique=True, index=True)  # Celery task ID
    workflow_id = Column(String(100), ForeignKey("workflow_definitions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Request details
    user_request = Column(Text, nullable=False)
    request_metadata = Column(JSON, default=dict)
    
    # Execution state
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    current_step = Column(String(100))
    completed_steps = Column(JSON, default=list)
    
    # Results and data
    intermediate_results = Column(JSON, default=dict)
    final_result = Column(JSON)
    error_info = Column(JSON)
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    execution_time = Column(Integer)  # seconds
    
    # Relationships
    user = relationship("User", back_populates="workflows")
    workflow_definition = relationship("WorkflowDefinition", back_populates="executions")

class AgentRegistry(Base):
    """Registry for available agents"""
    __tablename__ = "agent_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    class_path = Column(String(255), nullable=False)  # Full Python class path
    description = Column(Text)
    configuration = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    version = Column(String(50), default="1.0.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ToolRegistry(Base):
    """Registry for available tools"""
    __tablename__ = "tool_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    class_path = Column(String(255), nullable=False)  # Full Python class path
    description = Column(Text)
    category = Column(String(100))  # research, synthesis, execution, etc.
    configuration = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    version = Column(String(50), default="1.0.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemMetrics(Base):
    """System metrics and monitoring data"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(String(255), nullable=False)
    metric_type = Column(String(50))  # counter, gauge, histogram
    labels = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ConversationMemory(Base):
    """Per-user conversation history for long-term memory injection."""
    __tablename__ = "conversation_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True, nullable=False)
    role = Column(String(20), nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)
    run_id = Column(String(100), index=True)    # links back to WorkflowExecution
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Audit log for tracking system activities"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(100))
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
