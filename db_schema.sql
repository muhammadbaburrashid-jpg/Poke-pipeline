PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS pokemon (id INTEGER PRIMARY KEY, name TEXT, height INTEGER, weight INTEGER, base_experience INTEGER, species_url TEXT);
CREATE TABLE IF NOT EXISTS type (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS pokemon_type (pokemon_id INTEGER, type_id INTEGER, slot INTEGER, PRIMARY KEY (pokemon_id, type_id));
CREATE TABLE IF NOT EXISTS ability (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS pokemon_ability (pokemon_id INTEGER, ability_id INTEGER, is_hidden BOOLEAN, slot INTEGER, PRIMARY KEY (pokemon_id, ability_id));
CREATE TABLE IF NOT EXISTS stat (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS pokemon_stat (pokemon_id INTEGER, stat_id INTEGER, base_stat INTEGER, effort INTEGER, PRIMARY KEY (pokemon_id, stat_id));
CREATE TABLE IF NOT EXISTS evolution (from_pokemon_id INTEGER, to_pokemon_id INTEGER, evolution_details TEXT, PRIMARY KEY (from_pokemon_id, to_pokemon_id));
