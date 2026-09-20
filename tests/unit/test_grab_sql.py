from ai.grab_sql import grab_sql


def test_grab_sql(tmp_path):

    # Create a temporary dbt project
    dbt_project = tmp_path / "zomato"

    models_folder = dbt_project / "models"
    models_folder.mkdir(parents=True)

    # Create sample SQL files
    (models_folder / "orders.sql").write_text(
        "SELECT * FROM orders;",
        encoding="utf-8"
    )

    (models_folder / "users.sql").write_text(
        "SELECT * FROM users;",
        encoding="utf-8"
    )

    # Run the actual function
    output_file = grab_sql(dbt_project)

    # Check that the output file was created
    assert output_file.exists()

    # Read the generated text
    content = output_file.read_text(encoding="utf-8")

    # Check that the SQL files were included
    assert "orders.sql" in content
    assert "users.sql" in content

    # Check that the SQL content was copied
    assert "SELECT * FROM orders;" in content
    assert "SELECT * FROM users;" in content