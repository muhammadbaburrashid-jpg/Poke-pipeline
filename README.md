# PokéPipeline
PokéPipeline is an  ETL (Extract–Transform–Load) data pipeline that fetches Pokémon data from the public PokeAPI, transforms the nested JSON responses into normalized relational tables, and stores them in a SQL database - SQLite
This project demonstrates practical data engineering concepts, e.g., API integration, data modeling, normalization, transformation, and persistence; all implemented in Python with clean, reproducible code.
# Features:
•	Fetches Pokémon data dynamically from the PokeAPI.
•	Extracts name, height, weight, base experience, types, abilities, and base stats.
•	Transforms nested JSON responses into normalized relational tables.
•	Loads data into a SQLite database (pokemon.db).
•	Includes a Dockerfile for containerized execution.

# Instructions to setup and run the solution:
i: Install dependencies:
pip install -r requirements.txt

ii: Run the pipeline
python pipeline.py --limit 20 --db pokemon.db
This will:
•	Fetch 20 Pokémon records from the API
•	Transform and load them into the SQLite database (pokemon.db)
You can verify the data using any SQLite viewer:
sqlite3 pokemon.db
sqlite> SELECT * FROM pokemon LIMIT 20;

iii. Run with Docker (optional)
docker build -t poke-pipeline
docker run -it poke-pipeline

# Design Choices:
Data Extraction
•	Pokémon data is retrieved from https://pokeapi.co/api/v2.
•	Each Pokémon’s detailed attributes (types, abilities, stats) are fetched from its specific URL.
Data Transformation
•	Nested JSON responses from the API are flattened and normalized for SQL storage.
•	The transformation logic ensures that many-to-many relationships (like Pokémon types or abilities) are properly represented through join tables.
# Database Schama Design:
Table	Description
• pokemon -->	Core Pokémon entity with general attributes
• type -->	Master table of all Pokémon types
• pokemon_type -->	Mapping of Pokémon to their types (many-to-many)
• ability -->	Master table of Pokémon abilities
• pokemon_ability -->	Mapping of Pokémon to their abilities
• stat -->	Master table of base stats
• pokemon_stat -->	Mapping of Pokémon to their stats
• evolution -->	Evaluation details

# Data Loading:
•	Uses SQLite for ease of setup and portability.
•	Upsert logic prevents duplicate entries for reusable entities such as abilities and types.

# Assumptions:
•	Pokémon data from the API is consistent and valid JSON.
•	The PokeAPI structure remains stable (no schema changes).
•	SQLite is suitable for demo purposes; production would use PostgreSQL
•	The solution is limited to the first 20 Pokémon for demonstration.

# Potential Improvements:
•	Implementing a GraphQL API – Expose Pokémon data for flexible querying.
•	Adding Logging & Error Handling – Implement structured logging, retries, and graceful error recovery.
•	Parallel Data Fetching – Use multithreading to speed up API calls.
•	Docker Compose Support – Add PostgreSQL and pgAdmin services for persistent storage.
•	Unit Tests – Validate transformation logic and database integrity using pytest.



