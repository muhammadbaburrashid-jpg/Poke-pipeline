#!/usr/bin/env python3
"""
PokéPipeline: fetches Pokemon data from PokeAPI, transforms, and loads into SQLite.

Usage:::
    python pipeline.py --limit 20 --db pokemon.db
"""

import argparse
import requests
import sqlite3
import time
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm

POKEAPI_BASE = "https://pokeapi.co/api/v2"

# Simple helpers for DB operations
def init_db(conn: sqlite3.Connection):
    with open("db_schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()

def upsert_lookup(conn: sqlite3.Connection, table: str, name: str) -> int:
    """
    Insert into lookup table if not exists and return id.
    table: 'type', 'ability', 'stat'
    """
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid

def insert_pokemon(conn: sqlite3.Connection, p: Dict[str, Any]):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO pokemon (id, name, height, weight, base_experience, species_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (p["id"], p["name"], p.get("height"), p.get("weight"), p.get("base_experience"), p.get("species_url")),
    )
    conn.commit()

def insert_types(conn: sqlite3.Connection, pokemon_id: int, types: List[Dict[str, Any]]):
    for t in types:
        type_name = t["type"]["name"]
        slot = t.get("slot")
        tid = upsert_lookup(conn, "type", type_name)
        # upsert relation
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO pokemon_type (pokemon_id, type_id, slot)
            VALUES (?, ?, ?)
        """, (pokemon_id, tid, slot))
    conn.commit()

def insert_abilities(conn: sqlite3.Connection, pokemon_id: int, abilities: List[Dict[str, Any]]):
    for a in abilities:
        ability_name = a["ability"]["name"]
        slot = a.get("slot")
        is_hidden = 1 if a.get("is_hidden") else 0
        aid = upsert_lookup(conn, "ability", ability_name)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO pokemon_ability (pokemon_id, ability_id, is_hidden, slot)
            VALUES (?, ?, ?, ?)
        """, (pokemon_id, aid, is_hidden, slot))
    conn.commit()

def insert_stats(conn: sqlite3.Connection, pokemon_id: int, stats: List[Dict[str, Any]]):
    for s in stats:
        stat_name = s["stat"]["name"]
        base_stat = s.get("base_stat")
        effort = s.get("effort")
        sid = upsert_lookup(conn, "stat", stat_name)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO pokemon_stat (pokemon_id, stat_id, base_stat, effort)
            VALUES (?, ?, ?, ?)
        """, (pokemon_id, sid, base_stat, effort))
    conn.commit()

def insert_evolution_edge(conn: sqlite3.Connection, from_id: int, to_id: Optional[int], details: Optional[str]):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO evolution (from_pokemon_id, to_pokemon_id, evolution_details)
        VALUES (?, ?, ?)
    """, (from_id, to_id, details))
    conn.commit()

# API helpers
def get_json(url: str, max_retries=3, backoff=0.5) -> Optional[Dict[str, Any]]:
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"Warning: {url} returned status {r.status_code}")
                time.sleep(backoff * (attempt + 1))
        except Exception as e:
            print("Error fetching", url, e)
            time.sleep(backoff * (attempt + 1))
    return None

def fetch_pokemon_list(limit=20, offset=0) -> List[Dict[str, Any]]:
    url = f"{POKEAPI_BASE}/pokemon?limit={limit}&offset={offset}"
    j = get_json(url)
    if not j:
        return []
    return j.get("results", [])

def fetch_pokemon_detail(url: str) -> Optional[Dict[str, Any]]:
    return get_json(url)

def fetch_species(url: str) -> Optional[Dict[str, Any]]:
    return get_json(url)

def fetch_evolution_chain(url: str) -> Optional[Dict[str, Any]]:
    return get_json(url)

# Evolution chain flattening helper
def parse_evolution_chain(chain: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Walk the evolution chain and return list of (from_species_name, to_species_name, details_str)
    details_str is a summarized string (e.g., "level 16") for the evolution trigger.
    """
    edges = []
    def walk(node):
        from_name = node["species"]["name"]
        for evo in node.get("evolves_to", []):
            to_name = evo["species"]["name"]
            # summarize details
            details = evo.get("evolution_details", [])
            details_summary = []
            for d in details:
                trigger = d.get("trigger", {}).get("name")
                min_level = d.get("min_level")
                item = d.get("item", {}).get("name") if d.get("item") else None
                summary = f"trigger={trigger}"
                if min_level:
                    summary += f";min_level={min_level}"
                if item:
                    summary += f";item={item}"
                details_summary.append(summary)
            details_str = "|".join(details_summary) if details_summary else None
            edges.append((from_name, to_name, details_str))
            walk(evo)
    walk(chain["chain"])
    return edges

# Mapping helper: get pokemon id by species name via API (or from DB)
def species_name_to_pokemon_id(conn: sqlite3.Connection, species_name: str) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("SELECT id FROM pokemon WHERE name = ?", (species_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    return None

def main(limit: int, db_path: str):
    conn = sqlite3.connect(db_path)
    init_db(conn)

    # 1) fetch list of pokemon (name + url)
    pokemon_list = fetch_pokemon_list(limit=limit)
    print(f"Fetched list of {len(pokemon_list)} Pokémon to process.")

    # Keep a map name->id to help with evolution linking
    name_id_map = {}

    # 2) For each pokemon, fetch detail + species, insert core + related tables
    for entry in tqdm(pokemon_list, desc="Processing Pokémon"):
        url = entry["url"]
        detail = fetch_pokemon_detail(url)
        if not detail:
            print(f"Failed to fetch details for {entry['name']}")
            continue

        # Transform: flatten relevant fields
        p = {
            "id": detail["id"],
            "name": detail["name"],
            "height": detail.get("height"),
            "weight": detail.get("weight"),
            "base_experience": detail.get("base_experience"),
            "species_url": detail.get("species", {}).get("url")
        }

        insert_pokemon(conn, p)
        name_id_map[p["name"]] = p["id"]

        # types
        insert_types(conn, p["id"], detail.get("types", []))
        # abilities
        insert_abilities(conn, p["id"], detail.get("abilities", []))
        # stats
        insert_stats(conn, p["id"], detail.get("stats", []))

    # 3) After core insertions, go back and resolve evolution chains for the species we have.
    # We'll iterate again to fetch species -> evolution_chain -> create edges (if targets exist in our DB)
    for name, pid in tqdm(name_id_map.items(), desc="Processing evolution chains"):
        # fetch species
        cur = conn.cursor()
        cur.execute("SELECT species_url FROM pokemon WHERE id = ?", (pid,))
        row = cur.fetchone()
        if not row:
            continue
        species_url = row[0]
        if not species_url:
            continue
        species = fetch_species(species_url)
        if not species:
            continue
        evo_chain_info = species.get("evolution_chain")
        if not evo_chain_info:
            continue
        evo_chain_url = evo_chain_info.get("url")
        if not evo_chain_url:
            continue
        evo_chain = fetch_evolution_chain(evo_chain_url)
        if not evo_chain:
            continue
        edges = parse_evolution_chain(evo_chain)
        # edges are (from_species_name, to_species_name, details_str)
        for from_name, to_name, details in edges:
            # attempt to resolve both species to pokemon ids (may not exist in our limited fetch)
            from_id = species_name_to_pokemon_id(conn, from_name)
            to_id = species_name_to_pokemon_id(conn, to_name)
            # We will insert edge using from_id (if exists). If to_id is None, still insert with NULL or skip alternate logic.
            if from_id:
                insert_evolution_edge(conn, from_id, to_id, details)
    conn.close()
    print("Pipeline finished. DB:", db_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PokéPipeline ETL")
    parser.add_argument("--limit", type=int, default=20, help="how many pokemon to fetch")
    parser.add_argument("--db", type=str, default="pokemon.db", help="sqlite db file path")
    args = parser.parse_args()
    main(args.limit, args.db)
