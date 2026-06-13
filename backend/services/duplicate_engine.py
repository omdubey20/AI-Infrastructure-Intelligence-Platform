from collections import defaultdict


def analyze_duplicates(discoveries):

    grouped = defaultdict(list)

    for item in discoveries:
        grouped[item.project_name.lower()].append(item)

    results = []

    for project_name, copies in grouped.items():

        if len(copies) == 1:

            project = copies[0]

            results.append({
                "id": project.id,
                "project_name": project.project_name,
                "duplicate_confidence": 0,
                "reason": "Single project instance",
                "recommendation": "KEEP"
            })

            continue

        live_copy = None

        for copy in copies:
            if copy.dns_points_here and copy.web_config_active:
                live_copy = copy
                break

        for copy in copies:

            if live_copy and copy.id == live_copy.id:

                results.append({
                    "id": copy.id,
                    "project_name": copy.project_name,
                    "duplicate_confidence": 100,
                    "reason": "Live production copy",
                    "recommendation": "KEEP"
                })

            else:

                confidence = 95

                results.append({
                    "id": copy.id,
                    "project_name": copy.project_name,
                    "duplicate_confidence": confidence,
                    "reason": "Duplicate copy detected",
                    "recommendation": "DELETE"
                })

    return results