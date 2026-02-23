"""SQLAlchemy models for Hybrid Cloud Controller database schema."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    LargeBinary,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class UserModel(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    sessions = relationship("SessionModel", back_populates="user")
    configurations = relationship("ConfigurationModel", back_populates="user")
    credentials = relationship("CredentialModel", back_populates="user")


class SessionModel(Base):
    """User session model for authentication."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, default=True)

    # Relationships
    user = relationship("UserModel", back_populates="sessions")


class ConfigurationModel(Base):
    """User configuration model for compute, storage, network, and workload specs."""

    __tablename__ = "configurations"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Compute specifications
    cpu_cores = Column(Integer, nullable=False)
    memory_gb = Column(Integer, nullable=False)
    instance_count = Column(Integer, nullable=False)

    # Storage specifications
    storage_type = Column(String(50), nullable=False)
    storage_capacity_gb = Column(Integer, nullable=False)
    storage_iops = Column(Integer)

    # Network specifications
    bandwidth_mbps = Column(Integer, nullable=False)
    monthly_data_transfer_gb = Column(Integer, nullable=False)

    # Workload profile
    utilization_percentage = Column(Integer, nullable=False)
    operating_hours_per_month = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="configurations")
    tco_results = relationship("TCOResultModel", back_populates="configuration")
    provisions = relationship("ProvisionModel", back_populates="configuration")


class TCOResultModel(Base):
    """TCO calculation result model."""

    __tablename__ = "tco_results"

    id = Column(String(36), primary_key=True)
    configuration_id = Column(String(36), ForeignKey("configurations.id"), nullable=False)
    on_prem_costs_json = Column(Text, nullable=False)  # JSON serialized
    aws_costs_json = Column(Text, nullable=False)  # JSON serialized
    recommendation = Column(Text)
    calculated_at = Column(DateTime, nullable=False)

    # Relationships
    configuration = relationship("ConfigurationModel", back_populates="tco_results")


class PricingDataModel(Base):
    """AWS pricing data model."""

    __tablename__ = "pricing_data"

    id = Column(String(36), primary_key=True)
    ec2_pricing_json = Column(Text, nullable=False)
    ebs_pricing_json = Column(Text, nullable=False)
    s3_pricing_json = Column(Text, nullable=False)
    data_transfer_pricing_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, nullable=False)


class ProvisionModel(Base):
    """Provisioning operation model."""

    __tablename__ = "provisions"

    id = Column(String(36), primary_key=True)
    configuration_id = Column(String(36), ForeignKey("configurations.id"), nullable=False)
    cloud_path = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    configuration = relationship("ConfigurationModel", back_populates="provisions")
    resources = relationship("ResourceModel", back_populates="provision")
    terraform_state = relationship(
        "TerraformStateModel", back_populates="provision", uselist=False
    )


class ResourceModel(Base):
    """Provisioned resource model."""

    __tablename__ = "resources"

    id = Column(String(36), primary_key=True)
    provision_id = Column(String(36), ForeignKey("provisions.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    connection_info_json = Column(Text)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    provision = relationship("ProvisionModel", back_populates="resources")
    metrics = relationship("MetricsModel", back_populates="resource")


class TerraformStateModel(Base):
    """Terraform state model for tracking infrastructure state."""

    __tablename__ = "terraform_states"

    id = Column(String(36), primary_key=True)
    provision_id = Column(String(36), ForeignKey("provisions.id"), nullable=False)
    terraform_files = Column(Text, nullable=False)
    state_file = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    provision = relationship("ProvisionModel", back_populates="terraform_state")


class CredentialModel(Base):
    """Encrypted credential model for storing sensitive data."""

    __tablename__ = "credentials"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    credential_type = Column(String(50), nullable=False)
    encrypted_value = Column(LargeBinary, nullable=False)
    iv = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="credentials")


class MetricsModel(Base):
    """Resource metrics model for monitoring."""

    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True)
    resource_id = Column(String(36), ForeignKey("resources.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    storage_used_gb = Column(Float, nullable=False)
    storage_iops = Column(Float, nullable=False)
    network_in_mbps = Column(Float, nullable=False)
    network_out_mbps = Column(Float, nullable=False)

    # Relationships
    resource = relationship("ResourceModel", back_populates="metrics")


class ConversationModel(Base):
    """Conversation message model for Q&A service."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    configuration_id = Column(String(36), ForeignKey("configurations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
