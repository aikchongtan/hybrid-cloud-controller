# Bugfix Requirements Document

## Introduction

This bugfix addresses two critical issues blocking UAT completion in the Hybrid Cloud Controller application. Both issues stem from missing proxy endpoints in the Web UI layer that prevent the frontend from communicating with the API service. Issue #14 affects all three provisioning features (AWS, IaaS, CaaS), and Issue #15 affects the monitoring dashboard. These are systemic architecture issues following the same pattern as previously fixed Issues #10 and #11.

The application uses a two-tier architecture where the Web UI (port 10001) serves HTML pages and forwards API requests to the API service (port 10000). When proxy endpoints are missing, JavaScript API calls fail with authentication/CORS errors, resulting in "Load failed" errors visible to users.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user submits an AWS provisioning request THEN the system fails with "Provisioning failed: Load failed" error and no resources are created in LocalStack

1.2 WHEN a user submits an On-Premises IaaS provisioning request THEN the system fails with "Provisioning failed: Load failed" error and no virtual machines are simulated

1.3 WHEN a user submits an On-Premises CaaS provisioning request THEN the system fails with "Provisioning failed: Load failed" error and no containers are deployed

1.4 WHEN a user checks provisioning status for any provision ID THEN the system returns 404 error because the status endpoint is not proxied

1.5 WHEN a user retrieves provisioning details for any provision ID THEN the system returns 404 error because the details endpoint is not proxied

1.6 WHEN the monitoring dashboard loads and requests the resource list THEN the system fails with "Failed to load monitoring data" error and no resources are displayed

1.7 WHEN the monitoring dashboard requests metrics for a specific resource THEN the system fails with "Failed to load monitoring data" error and no metrics are displayed

1.8 WHEN the monitoring dashboard requests metrics with a time range parameter THEN the system fails because the time_range parameter is not forwarded to the API

### Expected Behavior (Correct)

2.1 WHEN a user submits an AWS provisioning request THEN the system SHALL forward the request to the API service with authentication, provision resources in LocalStack (EC2, EBS, S3, networking), and return the provision ID

2.2 WHEN a user submits an On-Premises IaaS provisioning request THEN the system SHALL forward the request to the API service with authentication, simulate virtual machine provisioning, and return the provision ID with SSH details

2.3 WHEN a user submits an On-Premises CaaS provisioning request THEN the system SHALL forward the request to the API service with authentication, deploy containers, and return the provision ID with container details

2.4 WHEN a user checks provisioning status for a provision ID THEN the system SHALL forward the status request to the API service with authentication and return the current provisioning status (pending, in_progress, completed, failed)

2.5 WHEN a user retrieves provisioning details for a provision ID THEN the system SHALL forward the details request to the API service with authentication and return complete provisioning information including resource IDs and configuration

2.6 WHEN the monitoring dashboard loads and requests the resource list THEN the system SHALL forward the request to the API service with authentication and return the list of all provisioned resources

2.7 WHEN the monitoring dashboard requests metrics for a specific resource THEN the system SHALL forward the request to the API service with authentication and return metrics data (CPU, memory, storage, network)

2.8 WHEN the monitoring dashboard requests metrics with a time range parameter THEN the system SHALL forward the time_range parameter to the API service and return metrics for the specified time period

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user accesses the provisioning page without authentication THEN the system SHALL CONTINUE TO return 401 authentication error

3.2 WHEN a user accesses the monitoring dashboard without authentication THEN the system SHALL CONTINUE TO return 401 authentication error

3.3 WHEN the API service is unavailable or times out THEN the system SHALL CONTINUE TO return appropriate error messages (503 for connection errors, 504 for timeouts)

3.4 WHEN a user requests status for a non-existent provision ID THEN the system SHALL CONTINUE TO return 404 error from the API

3.5 WHEN a user requests metrics for a non-existent resource ID THEN the system SHALL CONTINUE TO return 404 error from the API

3.6 WHEN existing proxy endpoints (Q&A, configuration validation) are called THEN the system SHALL CONTINUE TO function correctly without any changes

3.7 WHEN a user navigates to the provisioning or monitoring pages THEN the system SHALL CONTINUE TO render the HTML pages correctly

3.8 WHEN the API returns validation errors for provisioning requests THEN the system SHALL CONTINUE TO forward those errors to the frontend with appropriate status codes
