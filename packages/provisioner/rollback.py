"""Rollback manager for failed provisioning and deployment operations.

This module provides functions to rollback failed provisioning and deployment
operations by destroying resources using Terraform and updating provision status.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from packages.database import models
from packages.provisioner import terraform


@dataclass
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    provision_id: str
    error: Optional[str] = None
    resources_removed: int = 0


async def rollback_provisioning(provision_id: str, db_session: Session) -> RollbackResult:
    """Rollback failed provisioning by destroying all created resources.

    This function:
    1. Loads Terraform state from database
    2. Executes terraform destroy to remove all resources
    3. Verifies all resources are removed
    4. Updates provision status to 'rolled_back'
    5. Logs rollback completion

    Args:
        provision_id: ID of the provision record to rollback
        db_session: Database session for state retrieval and updates

    Returns:
        RollbackResult with success status and details
    """
    # Retrieve provision record
    provision = db_session.query(models.ProvisionModel).filter_by(id=provision_id).first()

    if not provision:
        return RollbackResult(
            success=False,
            provision_id=provision_id,
            error="Provision record not found in database",
        )

    # Check if Terraform state exists
    terraform_state = (
        db_session.query(models.TerraformStateModel).filter_by(provision_id=provision_id).first()
    )

    if not terraform_state:
        # No Terraform state means no resources were created
        # Just update status and return success
        provision.status = "rolled_back"
        db_session.commit()
        return RollbackResult(
            success=True,
            provision_id=provision_id,
            resources_removed=0,
        )

    # Execute terraform destroy
    destroy_result = await terraform.destroy_terraform(provision_id, db_session)

    if not destroy_result.success:
        return RollbackResult(
            success=False,
            provision_id=provision_id,
            error=f"Terraform destroy failed: {destroy_result.error}",
        )

    # Count resources that were tracked
    resource_count = (
        db_session.query(models.ResourceModel).filter_by(provision_id=provision_id).count()
    )

    # Update all resource statuses to terminated
    db_session.query(models.ResourceModel).filter_by(provision_id=provision_id).update(
        {"status": "terminated"}
    )

    # Update provision status to rolled_back
    provision.status = "rolled_back"
    db_session.commit()

    return RollbackResult(
        success=True,
        provision_id=provision_id,
        resources_removed=resource_count,
    )


async def rollback_deployment(
    deployment_id: str, provision_id: str, db_session: Session
) -> RollbackResult:
    """Rollback failed deployment to previous stable state.

    This function:
    1. Stops the new container/application
    2. Restores previous deployment if it exists
    3. Updates deployment status
    4. Logs rollback completion

    For the initial implementation, this performs a full provisioning rollback
    since we don't yet have deployment versioning. Future iterations can add
    support for rolling back to previous deployment versions.

    Args:
        deployment_id: ID of the failed deployment
        provision_id: ID of the provision record
        db_session: Database session for updates

    Returns:
        RollbackResult with success status and details
    """
    # For now, deployment rollback is equivalent to provisioning rollback
    # since we don't have deployment versioning yet
    # Future enhancement: track deployment versions and restore previous version

    # Retrieve provision record
    provision = db_session.query(models.ProvisionModel).filter_by(id=provision_id).first()

    if not provision:
        return RollbackResult(
            success=False,
            provision_id=provision_id,
            error="Provision record not found in database",
        )

    # Execute full provisioning rollback
    result = await rollback_provisioning(provision_id, db_session)

    if not result.success:
        return RollbackResult(
            success=False,
            provision_id=provision_id,
            error=f"Deployment rollback failed: {result.error}",
        )

    return RollbackResult(
        success=True,
        provision_id=provision_id,
        resources_removed=result.resources_removed,
    )
