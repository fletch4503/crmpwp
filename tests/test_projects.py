import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from projects.models import Project


class TestProjectModel:
    """Test Project model functionality."""

    def test_project_creation(self, user, company):
        """Test basic project creation."""
        project = baker.make(
            Project,
            user=user,
            title="Test Project",
            description="Test description",
            inn=company.inn if company else None,
        )
        assert project.title == "Test Project"
        assert project.description == "Test description"
        assert project.user == user
        assert project.status == "draft"  # Default status

    def test_project_str(self, user):
        """Test project string representation."""
        project = baker.make(Project, user=user, title="My Project")
        assert str(project) == "My Project"

    def test_project_status_choices(self, user):
        """Test project status choices."""
        valid_statuses = ["draft", "active", "completed", "on_hold", "cancelled"]
        for project_status in valid_statuses:
            project = baker.make(Project, user=user, status=project_status)
            assert project.status == project_status

    def test_project_priority_choices(self, user):
        """Test project priority choices."""
        valid_priorities = ["low", "medium", "high", "urgent"]
        for priority in valid_priorities:
            project = baker.make(Project, user=user, priority=priority)
            assert project.priority == priority


class TestProjectViews:
    """Test project-related views."""

    def test_project_list_requires_auth(self, client):
        """Test that project list requires authentication."""
        response = client.get(reverse("projects:project_list"))
        assert response.status_code == 302  # Redirect to login

    def test_project_list_authenticated(self, authenticated_client):
        """Test project list view for authenticated user."""
        response = authenticated_client.get(reverse("projects:project_list"))
        assert response.status_code == 200

    def test_project_create_view(self, authenticated_client):
        """Test project creation view."""
        response = authenticated_client.get(reverse("projects:project_create"))
        assert response.status_code == 200

    def test_project_detail_view(self, authenticated_client, project):
        """Test project detail view."""
        response = authenticated_client.get(
            reverse("projects:project_detail", kwargs={"pk": project.pk})
        )
        assert response.status_code == 200


class TestProjectAPIViews:
    """Test project API views."""

    def test_project_list_api(self, authenticated_client):
        """Test project list API endpoint."""
        response = authenticated_client.get("/api/projects/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_project_create_api(self, authenticated_client, company):
        """Test project creation via API."""
        data = {
            "title": "New Project",
            "description": "Project description",
            "status": "active",
            "priority": "high",
            "inn": company.inn if company else None,
        }
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Project"
        assert response.data["status"] == "active"

    def test_project_detail_api(self, authenticated_client, project):
        """Test project detail API endpoint."""
        response = authenticated_client.get(f"/api/projects/{project.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == project.title

    def test_project_update_api(self, authenticated_client, project):
        """Test project update via API."""
        data = {"title": "Updated Project Title", "status": "completed"}
        response = authenticated_client.patch(f"/api/projects/{project.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated Project Title"
        assert response.data["status"] == "completed"

    def test_project_delete_api(self, authenticated_client, project):
        """Test project deletion via API."""
        response = authenticated_client.delete(f"/api/projects/{project.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_project_search_api(self, authenticated_client, project):
        """Test project search functionality."""
        # Search by title
        response = authenticated_client.get(f"/api/projects/?search={project.title}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

        # Search by description
        response = authenticated_client.get(
            f"/api/projects/?search={project.description[:10]}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_project_filtering_api(self, authenticated_client, project):
        """Test project filtering."""
        # Filter by status
        response = authenticated_client.get(f"/api/projects/?status={project.status}")
        assert response.status_code == status.HTTP_200_OK

        # Filter by priority
        response = authenticated_client.get(
            f"/api/projects/?priority={project.priority}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Filter by INN
        if project.inn:
            response = authenticated_client.get(f"/api/projects/?inn={project.inn}")
            assert response.status_code == status.HTTP_200_OK

    def test_project_with_emails_api(
        self, authenticated_client, project, email_message
    ):
        """Test project with related emails API."""
        # Associate email with project
        email_message.related_project = project
        email_message.save()

        response = authenticated_client.get(f"/api/projects/{project.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Check if emails are included
        if "emails" in response.data:
            assert len(response.data["emails"]) > 0
        elif "emails_count" in response.data:
            assert response.data["emails_count"] > 0


class TestProjectPermissions:
    """Test project permissions."""

    def test_user_can_only_see_own_projects(self, authenticated_client, user):
        """Test that users can only see their own projects."""
        # Create project for the user
        project = baker.make(Project, user=user)

        # Create project for another user
        other_user = baker.make("users.User")
        other_project = baker.make(Project, user=other_user)

        response = authenticated_client.get("/api/projects/")
        project_ids = [p["id"] for p in response.data["results"]]

        assert project.id in project_ids
        assert other_project.id not in project_ids

    def test_user_can_modify_own_projects(self, authenticated_client, project):
        """Test that users can modify their own projects."""
        data = {"title": "Modified Project"}
        response = authenticated_client.patch(f"/api/projects/{project.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Modified Project"

    def test_user_cannot_modify_others_projects(self, authenticated_client):
        """Test that users cannot modify others' projects."""
        other_user = baker.make("users.User")
        other_project = baker.make(Project, user=other_user)

        data = {"title": "Modified Project"}
        response = authenticated_client.patch(
            f"/api/projects/{other_project.id}/", data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectValidation:
    """Test project data validation."""

    def test_project_status_validation(self, authenticated_client):
        """Test project status validation."""
        # Valid status
        data = {
            "title": "Valid Project",
            "description": "Description",
            "status": "active",
        }
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid status
        data["status"] = "invalid_status"
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data

    def test_project_priority_validation(self, authenticated_client):
        """Test project priority validation."""
        # Valid priority
        data = {
            "title": "Valid Project",
            "description": "Description",
            "priority": "high",
        }
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid priority
        data["priority"] = "invalid_priority"
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "priority" in response.data

    def test_project_title_required(self, authenticated_client):
        """Test that project title is required."""
        data = {"description": "Description without title", "status": "draft"}
        response = authenticated_client.post("/api/projects/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in response.data


class TestProjectWorkflow:
    """Test project workflow transitions."""

    def test_project_status_transitions(self, authenticated_client, project):
        """Test valid project status transitions."""
        # Draft -> Active
        data = {"status": "active"}
        response = authenticated_client.patch(f"/api/projects/{project.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.status == "active"

        # Active -> Completed
        data = {"status": "completed"}
        response = authenticated_client.patch(f"/api/projects/{project.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.status == "completed"

        # Completed -> Active (should be allowed)
        data = {"status": "active"}
        response = authenticated_client.patch(f"/api/projects/{project.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.status == "active"

    def test_project_bulk_status_update(self, authenticated_client):
        """Test bulk status update for projects."""
        # Create multiple projects
        projects_data = [
            {
                "title": f"Project {i}",
                "description": f"Description {i}",
                "status": "draft",
            }
            for i in range(3)
        ]

        created_projects = []
        for project_data in projects_data:
            response = authenticated_client.post("/api/projects/", project_data)
            assert response.status_code == status.HTTP_201_CREATED
            created_projects.append(response.data["id"])

        # Bulk update status
        bulk_data = {"projects": created_projects, "status": "active"}
        response = authenticated_client.post("/api/projects/bulk-status/", bulk_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify all projects were updated
        for project_id in created_projects:
            response = authenticated_client.get(f"/api/projects/{project_id}/")
            assert response.data["status"] == "active"


class TestProjectStatistics:
    """Test project statistics and analytics."""

    def test_project_stats_calculation(self, authenticated_client):
        """Test project statistics calculation."""
        # Create projects with different statuses
        baker.make(
            Project, user=authenticated_client.handler._force_user, status="draft"
        )
        baker.make(
            Project, user=authenticated_client.handler._force_user, status="active"
        )
        baker.make(
            Project, user=authenticated_client.handler._force_user, status="completed"
        )

        response = authenticated_client.get("/api/projects/stats/")
        assert response.status_code == status.HTTP_200_OK

        stats = response.data
        assert "total_projects" in stats
        assert "active_projects" in stats
        assert "completed_projects" in stats
        assert stats["total_projects"] >= 3

    def test_project_priority_distribution(self, authenticated_client):
        """Test project priority distribution."""
        # Create projects with different priorities
        priorities = ["low", "medium", "high", "urgent"]
        for priority in priorities:
            baker.make(
                Project,
                user=authenticated_client.handler._force_user,
                priority=priority,
            )

        response = authenticated_client.get("/api/projects/stats/")
        assert response.status_code == status.HTTP_200_OK

        stats = response.data
        if "priority_distribution" in stats:
            assert len(stats["priority_distribution"]) >= 4
