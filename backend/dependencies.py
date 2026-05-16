from db.supabase import supabase
from db.neo4j import neo4j_driver, get_neo4j_session
from db.ai import ai_client, clean_ai_json


def get_supabase_client():
    return supabase


def get_neo4j_driver():
    return neo4j_driver


def get_ai_client():
    return ai_client


def get_json_cleaner():
    return clean_ai_json
