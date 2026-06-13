from models import ProjectDiscovery


def discover_projects(db):
    """
    Simulates infrastructure scan.

    Later this will be replaced by:
    - SSH scanning
    - Nginx parsing
    - Apache parsing
    - DNS validation
    """

    return db.query(ProjectDiscovery).all()


def find_duplicate_projects(db):

    discoveries = discover_projects(db)

    grouped = {}

    for project in discoveries:

        grouped.setdefault(
            project.project_name.lower(),
            []
        ).append(project)

    duplicates = []

    for project_name, copies in grouped.items():

        if len(copies) > 1:

            live_copy = None

            for copy in copies:

                if (
                    copy.dns_points_here
                    and copy.web_config_active
                ):
                    live_copy = copy
                    break

            duplicates.append(
                {
                    "project_name": project_name,
                    "live_copy": live_copy,
                    "copies": copies
                }
            )

    return duplicates