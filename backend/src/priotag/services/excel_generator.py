"""Excel generation service."""

from typing import Any

import pandas as pd


class ExcelGenerator:
    """Service for generating Excel reports for priority data."""

    def generate_priorities_report(
        self, decrypted_users_data: list[dict[str, Any]], month: str, output_path: str
    ) -> str:
        """Generate Excel report from decrypted priority data.

        Args:
            decrypted_users_data: List of dictionaries containing:
                - userName: str - User's name
                - priorities: dict with 'weeks' list containing week data
            month: str - Month in format "YYYY-MM" or display format
            output_path: str - Path where Excel file should be saved

        Returns:
            str - Path to the generated Excel file
        """

        # Prepare data for DataFrame
        rows = []

        # Day labels for column headers
        day_labels = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
        day_keys = ["monday", "tuesday", "wednesday", "thursday", "friday"]

        for user_data in decrypted_users_data:
            user_name = user_data.get("userName", "Unbekannt")
            priorities = user_data.get("priorities", {})
            weeks = priorities.get("weeks", [])

            if not weeks:
                # User has no priority data
                row = {"Name": user_name}
                rows.append(row)
                continue

            # Sort weeks by week number
            sorted_weeks = sorted(weeks, key=lambda w: w.get("weekNumber", 0))

            # Create a row for this user with all their week data
            row = {"Name": user_name}

            for week in sorted_weeks:
                week_number = week.get("weekNumber", 0)

                # Add each day's priority for this week
                for day_key, day_label in zip(day_keys, day_labels):
                    priority = week.get(day_key)
                    column_name = f"KW{week_number} {day_label}"

                    # Convert priority to readable format
                    if priority is None:
                        row[column_name] = ""
                    else:
                        row[column_name] = priority

            rows.append(row)

        # Create DataFrame and save to Excel
        df = pd.DataFrame(rows)

        # Sort by name for better readability
        if not df.empty and "Name" in df.columns:
            df = df.sort_values("Name")

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(
                writer, sheet_name=f"Prioritäten {month}", index=False, na_rep=""
            )

            # Auto-adjust columns width
            worksheet = writer.sheets[f"Prioritäten {month}"]

            for column in worksheet.columns:
                max_length = 0
                column_cells = list(column)
                for cell in column_cells:
                    try:
                        cell_value = str(cell.value) if cell.value is not None else ""
                        if len(cell_value) > max_length:
                            max_length = len(cell_value)
                    except (ValueError, AttributeError):
                        pass

                # Set width with min of 10 and max of 50
                adjusted_width = min(max(max_length + 2, 10), 50)
                worksheet.column_dimensions[
                    column_cells[0].column_letter
                ].width = adjusted_width

        return output_path
