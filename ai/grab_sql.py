# ai/grab_sql.py

from pathlib import Path


def grab_sql(dbt_project):
    """
    Collect all SQL files from a dbt project
    and write their contents into one text file.
    """

    dbt_project = Path(dbt_project)

    output_file = dbt_project / "all_sql_files.txt"

    sql_files = sorted(dbt_project.rglob("*.sql"))

    with open(output_file, "w", encoding="utf-8") as output:

        for sql_file in sql_files:

            if sql_file == output_file:
                continue

            output.write("\n" + "=" * 80 + "\n")
            output.write(
                f"FILE: {sql_file.relative_to(dbt_project)}\n"
            )
            output.write("=" * 80 + "\n\n")

            with open(sql_file, "r", encoding="utf-8") as file:
                output.write(file.read())

            output.write("\n\n")

    return output_file


if __name__ == "__main__":

    dbt_project = Path(
        r"C:\Users\a4ala\Desktop\work\projects\zomato_pipeline\zomato"
    )

    output_file = grab_sql(dbt_project)

    print("SQL files copied into:")
    print(output_file)